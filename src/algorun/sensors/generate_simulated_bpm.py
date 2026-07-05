# il seguente codice crea un dataset finto di battiti cardiaci, rendendo
# possibile lo sviluppo ed il test senza avere subito registrazioni reali


# il codice nel complesso lavora in questo modo:


#  Definisce 2 utenti finti
#          ↓
#  Definisce 3 tipi di allenamento
#          ↓
#  Simula come cambiano i BPM durante ogni allenamento
#          ↓
#  Aggiunge piccole oscillazioni e rumore
#          ↓
#  Crea 6 sessioni totali
#          ↓
#  Salva tutto in bpm_sessions.csv






#  vengono utilizzate le librerie:
#    - path per gestire cartelle e file
#    - numpy per generare numeri, curve e rumore
#    - pandas per creare tabella e salvarla come CSV



from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd





#  il seed rappresenta il valore iniziale da cui parte l'algoritmo di generazione
#  di numeri casuali (crea sempre la stessa sequenza di numeri ogni volta che si esegue)

#  il sampling rate indica quante misurazioni vengono fatte al secondo

#  la session duration indica la durata di ogni sessione (in questo caso 10 minuti)


RANDOM_SEED = 42                   
SAMPLING_RATE_HZ = 1
SESSION_DURATION_SECONDS = 600



#  vengono creati 2 utenti diversi

USER_PROFILES = {
    "U01": {
        "resting_hr": 58,
        "max_hr": 198,
    },
    "U02": {
        "resting_hr": 64,
        "max_hr": 192,
    },
}




#  vengono simulati 3 tipi di allenamento (easy, moderate, interval)
#  ogni allenamento è diviso in fasi (warmup, steady, recovery)

#  la struttura di ogni tupla è:
#  (secondo iniziale, secondo finale, offset BPM iniziale, offset BPM finale, fase)


SESSION_TEMPLATES = {
    "easy": [        
        (0, 120, 5, 35, "warmup"),                  # la fase warmup dura dal secondo 0 al 120, il BPM iniziale è BMP a riposo + 5, il BPM finale è BMP a riposo + 35
        (120, 420, 35, 65, "steady"),
        (420, 600, 65, 20, "recovery"),
    ],
    "moderate": [
        (0, 100, 5, 40, "warmup"),
        (100, 400, 40, 90, "steady"),
        (400, 500, 90, 105, "hard"),
        (500, 600, 105, 30, "recovery"),
    ],
    "interval": [
        (0, 90, 5, 40, "warmup"),
        (90, 180, 40, 100, "hard"),
        (180, 240, 100, 60, "recovery"),
        (240, 330, 60, 110, "hard"),
        (330, 390, 110, 65, "recovery"),
        (390, 480, 65, 115, "hard"),
        (480, 600, 115, 25, "recovery"),
    ],
}




#  la seguente funzione genera i BPM per una singola fase

def generate_segment(
    start_second: int,
    end_second: int,
    start_bpm: float,
    end_bpm: float,
    rng: np.random.Generator,
) -> np.ndarray:

    #durata della fase
    length = end_second - start_second        

    if length <= 0:
        raise ValueError("The segment must have a positive duration.")


    #crea valori graduali fra BPM iniziale e finale
    linear_component = np.linspace(
        start_bpm,
        end_bpm,                       
        num=length,
        endpoint=False,
    )


    #viene aggiunta un'oscillazione con la funzione seno
    #rendendo il segnale meno perfettamente lineare
    periodic_component = 1.5 * np.sin(
        np.linspace(0, 4 * np.pi, num=length)
    )


    #viene introdotto un rumore che aggiunge piccoli errori/variazioni casuali
    #simulando imprecisione del sensore/piccoli cambiamenti durante la corsa
    noise = rng.normal(
        loc=0.0,
        scale=1.2,
        size=length,
    )


    #ogni valore BPM = andamento generale + oscillazione + rumore
    return linear_component + periodic_component + noise




#  la seguente funzione genera un allenamento completo di 10 minuiti
#  ricevendo l'utente, tipo di allenamento, numero della sessione, generatore casuale

def generate_session(
    user_id: str,
    session_type: str,
    session_number: int,
    rng: np.random.Generator,
) -> pd.DataFrame:
    
    #viene recuperato il profilo dell'utente e le sue caratteristiche
    profile = USER_PROFILES[user_id]

    resting_hr = profile["resting_hr"]
    max_hr = profile["max_hr"]

    template = SESSION_TEMPLATES[session_type]

    rows: list[dict[str, object]] = []

    #il ciclo legge una fase alla volta
    for (
        start_second,
        end_second,
        start_offset,
        end_offset,
        phase,
    ) in template:
        start_bpm = resting_hr + start_offset
        end_bpm = resting_hr + end_offset

        #viene chiamata generate_segment() che genera tutti i BPM della fase
        segment_values = generate_segment(
            start_second=start_second,
            end_second=end_second,
            start_bpm=start_bpm,
            end_bpm=end_bpm,
            rng=rng,
        )

        #viene impedito che i valori diventino troppo bassi/alti per il rumore
        segment_values = np.clip(
            segment_values,
            resting_hr - 5,
            max_hr - 2,
        )

        for local_index, bpm in enumerate(segment_values):
            second = start_second + local_index

            #per ogni secondo della fase viene creata la seguente row
            rows.append(
                {
                    "session_id": (
                        f"{user_id}_S{session_number:02d}_{session_type}"      #es. U01_S02_moderate
                    ),
                    "user_id": user_id,
                    "second": second,
                    "bpm": round(float(bpm), 2),
                    "resting_hr": resting_hr,
                    "max_hr": max_hr,
                    "workout_goal": session_type,
                    "phase": phase,
                }
            )

    session_df = pd.DataFrame(rows)


    #ogni sessione da 10 minuti deve avere 600 rows
    if len(session_df) != SESSION_DURATION_SECONDS:
        raise RuntimeError(
            f"Session {session_type} has {len(session_df)} rows "
            f"instead of {SESSION_DURATION_SECONDS}."
        )

    return session_df


def main() -> None:
    #viene creato il generatore casuale
    rng = np.random.default_rng(RANDOM_SEED)

    sessions: list[pd.DataFrame] = []

    #vengono generate tutte le sessioni
    for user_id in USER_PROFILES:
        for session_number, session_type in enumerate(
            SESSION_TEMPLATES,
            start=1,
        ):
            session_df = generate_session(
                user_id=user_id,
                session_type=session_type,
                session_number=session_number,
                rng=rng,
            )

            sessions.append(session_df)

    #vengono unite tutte le sessioni in un'unica tabella
    final_df = pd.concat(
        sessions,
        ignore_index=True,
    )
    
    #indica dove salvare CSV
    output_path = Path(
        "data/simulated/bpm_sessions.csv"
    )

    #crea cartella data/simulated se non esiste 
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    #salva file senza aggiungere colonna degli indici
    final_df.to_csv(
        output_path,
        index=False,
    )

    print(f"Dataset saved to: {output_path}")
    print(f"Rows: {len(final_df)}")
    print(f"Sessions: {final_df['session_id'].nunique()}")
    print(f"Users: {final_df['user_id'].nunique()}")

    print("\nRows per session:")
    print(
        final_df.groupby("session_id")
        .size()
        .to_string()
    )

    print("\nBPM range:")
    print(
        final_df.groupby("user_id")["bpm"]
        .agg(["min", "mean", "max"])
        .round(2)
        .to_string()
    )


if __name__ == "__main__":
    main()
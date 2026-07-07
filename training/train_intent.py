"""Allena il classificatore d'intento (SetFit) — few-shot, gira su M2 in minuti.

5 tipi di corsa, ~12 frasi/classe prese dai trigger dei 5 tipi. SetFit basta con
pochi esempi. Encoder multilingue (italiano).

Uso:  python train_intent.py          # salva in models/intent-setfit/
"""
from datasets import Dataset
from setfit import SetFitModel, Trainer, TrainingArguments

# frasi -> tipo (dai trigger; aggiungine quante vuoi, migliora e basta)
TRAIN = [
    ("oggi corsa piano di recupero", "easy"), ("qualcosa di tranquillo, sono scarico", "easy"),
    ("corsetta chill senza fatica", "easy"), ("voglio solo sciogliere le gambe", "easy"),
    ("corsa lenta e rilassata", "easy"), ("oggi vado piano piano", "easy"),
    ("recupero blando, niente sforzo", "easy"), ("corsa leggera per rigenerarmi", "easy"),
    ("giro tranquillo di venti minuti", "easy"), ("oggi relax, corsa facile", "easy"),
    ("defaticante, molto piano", "easy"), ("easy run senza fretta", "easy"),

    ("oggi faccio il lungo", "long"), ("tanti chilometri a ritmo costante", "long"),
    ("corsa lunga per la resistenza", "long"), ("voglio andare lontano oggi", "long"),
    ("un'ora e mezza di corsa costante", "long"), ("lungo lento di venti km", "long"),
    ("macinare chilometri senza strappi", "long"), ("endurance, ritmo regolare", "long"),
    ("oggi fondo lungo", "long"), ("corsa lunga e ipnotica", "long"),
    ("tengo lo stesso passo per tanto", "long"), ("long run tranquillo ma lungo", "long"),

    ("corsa media, voglio spingere un po'", "tempo"), ("ritmo gara, veloce ma costante", "tempo"),
    ("oggi tempo run", "tempo"), ("faticoso ma gestibile", "tempo"),
    ("spingo sulla soglia", "tempo"), ("corsa sostenuta a ritmo medio", "tempo"),
    ("voglio andare forte ma controllato", "tempo"), ("corsa impegnativa a ritmo tenuto", "tempo"),
    ("medio deciso oggi", "tempo"), ("corro a dodici all'ora costante", "tempo"),
    ("ritmo tosto ma costante", "tempo"), ("soglia anaerobica, spinta", "tempo"),

    ("oggi ripetute veloci", "interval"), ("intervalli e scatti al massimo", "interval"),
    ("sei volte i mille metri", "interval"), ("scatti forti e recupero", "interval"),
    ("ripetute brevi ad alta intensità", "interval"), ("allenamento a intervalli", "interval"),
    ("sprint e pausa, ripetuti", "interval"), ("oggi si scatta", "interval"),
    ("lavoro con le ripetute", "interval"), ("un minuto forte e uno piano", "interval"),
    ("intervalli esplosivi", "interval"), ("massimo sforzo a ripetizioni", "interval"),

    ("oggi fartlek con variazioni", "fartlek"), ("cambi di passo come mi sento", "fartlek"),
    ("gioco di ritmi liberi", "fartlek"), ("corro e vario a sensazione", "fartlek"),
    ("variazioni non strutturate", "fartlek"), ("scatto quando mi va", "fartlek"),
    ("fartlek per divertirmi", "fartlek"), ("cambi di ritmo casuali", "fartlek"),
    ("quaranta minuti di variazioni", "fartlek"), ("corsa con accelerazioni libere", "fartlek"),
    ("seguo le gambe, cambi di passo", "fartlek"), ("speed play oggi", "fartlek"),

    # --- frasi aggiunte dal socio (etichette mappate sui 5 tipi) ---
    ("Corsa chill di 20 minuti", "easy"), ("Ho le gambe di legno, andiamo piano", "easy"),
    ("Scarico totale senza guardare il tempo", "easy"), ("Ritmo super blando oggi", "easy"),
    ("Passeggiata veloce per recuperare", "easy"), ("Oggi non voglio sudare troppo", "easy"),
    ("Corsa tranquilla intorno ai 120 battiti", "easy"), ("Solo una sgambata per muovere le gambe", "easy"),

    ("15 km a ritmo costante", "long"), ("Due ore di corsa senza fermarmi mai", "long"),
    ("Lungo lento per preparare la maratona", "long"), ("Oggi si macinano chilometri", "long"),
    ("Andatura ipnotica per 90 minuti", "long"), ("Voglio correre fino al tramonto a 6 al km", "long"),
    ("Resistenza pura, teniamo i 140 bpm a lungo", "long"), ("Mezza maratona di allenamento oggi", "long"),

    ("A 4 e 30 al km spaccati", "tempo"), ("Medio veloce per 40 minuti", "tempo"),
    ("Soglia anaerobica costante senza cedere", "tempo"), ("Oggi spingiamo a 12 all'ora fissi", "tempo"),
    ("Ritmo gara 10k da tenere fino alla fine", "tempo"), ("Corsa faticosa ma tenuta per 10 km", "tempo"),
    ("Voglio stare sui 160 battiti esatti", "tempo"), ("Andatura sfidante ma super regolare", "tempo"),

    ("Ripetute 8 per 1000 metri", "interval"), ("Un minuto a palla e un minuto camminando", "interval"),
    ("Scatti in salita e recupero in discesa", "interval"), ("400 metri alla morte poi stop", "interval"),
    ("Intervalli ad altissima intensità", "interval"), ("Massimo sforzo e poi recupero da fermo", "interval"),
    ("Voglio fare un frazionato di 5 km", "interval"), ("Onda quadra sui battiti, su e giù continuo", "interval"),

    ("Cambi di ritmo a sensazione", "fartlek"), ("Gioco di velocità nel bosco", "fartlek"),
    ("Variazioni libere per 40 minuti", "fartlek"), ("Oggi fartlek divertente", "fartlek"),
    ("Accelero solo quando mi va", "fartlek"), ("Corsa mista senza schemi rigidi", "fartlek"),
    ("Voglio variare tanto la velocità seguendo la musica", "fartlek"), ("Strappi improvvisi ma non programmati", "fartlek"),
]

# test tenuto fuori: frasi mie + gli adversarial/slang del socio (etichetta piu' difendibile)
TEST = [
    ("vado piano oggi, recupero", "easy"), ("solo sciogliere, tranquillo", "easy"),
    ("macino chilometri lenti", "long"), ("fondo lungo di un'ora", "long"),
    ("spingo a ritmo medio costante", "tempo"), ("tempo run impegnativo", "tempo"),
    ("ripetute da quattrocento veloci", "interval"), ("scatti al massimo con pause", "interval"),
    ("vario il ritmo a sensazione", "fartlek"), ("fartlek libero di trenta minuti", "fartlek"),
    # adversarial (slang / trabocchetti)
    ("Andiamo a smaltire la pizza di ieri senza nessuna fretta", "easy"),
    ("Velocità da nonno che guarda i cantieri, andiamo", "easy"),
    ("Fammela sudare tanto ma senza fare scatti improvvisi", "tempo"),
    ("Oggi ho un passo da Terminator, imposta una velocità costante e distruttiva", "tempo"),
    ("Non so cosa voglio fare oggi, fammi solo divertire con i ritmi", "fartlek"),
    ("Tantissimi chilometri ma voglio tornare a casa ancora vivo", "long"),
    ("Voglio avere il cuore in gola, ma a fasi alterne", "interval"),
    ("Oggi mettiamo il turbo al massimo finché non scoppio", "interval"),
]

ENCODER = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


def main() -> None:
    train_ds = Dataset.from_dict({"text": [t for t, _ in TRAIN], "label": [l for _, l in TRAIN]})
    model = SetFitModel.from_pretrained(ENCODER)
    trainer = Trainer(model=model, args=TrainingArguments(batch_size=16, num_epochs=1),
                      train_dataset=train_ds)
    trainer.train()
    model.save_pretrained("models/intent-setfit")

    ok = sum(model.predict([t])[0] == g for t, g in TEST)
    print(f"\nAccuracy sul test tenuto fuori: {ok}/{len(TEST)}")
    for t, g in TEST:
        p = model.predict([t])[0]
        print(f"  {'OK ' if p == g else 'X  '}{t!r:45} -> {p}  (atteso {g})")


if __name__ == "__main__":
    main()

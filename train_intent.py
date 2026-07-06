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
]

TEST = [
    ("vado piano oggi, recupero", "easy"), ("solo sciogliere, tranquillo", "easy"),
    ("macino chilometri lenti", "long"), ("fondo lungo di un'ora", "long"),
    ("spingo a ritmo medio costante", "tempo"), ("tempo run impegnativo", "tempo"),
    ("ripetute da quattrocento veloci", "interval"), ("scatti al massimo con pause", "interval"),
    ("vario il ritmo a sensazione", "fartlek"), ("fartlek libero di trenta minuti", "fartlek"),
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

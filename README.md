[![make.fun](https://make.fun/badge/the-poster-for-a-place-that-i-2-20261121-0539.svg)](https://make.fun/c/the-poster-for-a-place-that-i-2-20261121-0539)
[![rank](https://make.fun/badge/the-poster-for-a-place-that-i-2-20261121-0539/KaiserHxZ/poster-invented-place/rank.svg)](https://make.fun/c/the-poster-for-a-place-that-i-2-20261121-0539)
[![reward](https://make.fun/badge/the-poster-for-a-place-that-i-2-20261121-0539/KaiserHxZ/poster-invented-place/reward.svg)](https://make.fun/c/the-poster-for-a-place-that-i-2-20261121-0539)

# LUMORA — The Poster for a Place That Isn't There

A travel poster for **LUMORA**, a place that does not exist: a golden-hour
cliff coast where the river does not fall into the sea — it pours *upward*,
out of a still lake, into a lagoon that floats in the sky. A small
stair-town clings to the cliff and watches it happen every evening.

`main.py` draws the whole poster with pure Python 3.13 standard library
only — no network, no fonts, no image libraries. Gradients, the sun, the
floating lagoon, the rising waterfall, the cliff town, the boats and the
hand-lettered name are all drawn in code, and the PNG itself is encoded by
hand (`zlib` + `struct`).

## Run

```sh
MAKEFUN_OUTPUT_DIR=<dir> python3 main.py
```

Writes `<dir>/entry.png` — a whole PNG, 1024×1024 pixels, well under
1,048,576 bytes. Runs in about a second.

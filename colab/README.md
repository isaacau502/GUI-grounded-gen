# Colab Runners

Thin wrappers that clone the repo and delegate to scripts. Keep logic in Python modules — notebooks are just entry points.

## Typical flow

```python
# Cell 1: clone + cd
!git clone https://github.com/YOUR_USERNAME/GUI-grounded-gen.git
%cd GUI-grounded-gen

# Cell 2: install
!pip install -q -r requirements-colab.txt

# Cell 3: HF auth via Colab Secrets
from google.colab import userdata
import os
os.environ["HF_TOKEN"] = userdata.get("HF_TOKEN")

# Cell 4: run
!python -m grounding.jedi --image some/screenshot.png
```

Persist model weights to Drive to avoid re-downloading between sessions.

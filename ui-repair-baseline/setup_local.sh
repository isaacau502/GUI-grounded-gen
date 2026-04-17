#!/bin/bash
# One-time setup for running DesignBench repair locally.
# Run from this directory: cd ui-repair-baseline && bash setup_local.sh
set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
REPO_ROOT="$( cd "${SCRIPT_DIR}/.." && pwd )"
DESIGNBENCH_ROOT="${DESIGNBENCH_ROOT:-${REPO_ROOT}/external/DesignBench}"

if [ ! -d "${DESIGNBENCH_ROOT}" ]; then
  echo "ERROR: DesignBench not found at ${DESIGNBENCH_ROOT}"
  echo "Clone it first: git clone https://github.com/WebPAI/DesignBench.git ${DESIGNBENCH_ROOT}"
  exit 1
fi

echo "=== Installing Python packages ==="
pip install \
  anthropic \
  "openai>=1.50,<2" \
  selenium \
  opencv-python \
  scikit-image \
  pillow \
  numpy \
  scipy \
  openai-clip \
  ftfy \
  retry \
  imageio \
  python-dotenv \
  torch \
  torchvision

echo ""
echo "=== Installing npm AST parsers ==="
cd "${DESIGNBENCH_ROOT}"
npm install @babel/parser @vue/compiler-dom parse5

echo ""
echo "=== Installing web app dependencies ==="
cd "${DESIGNBENCH_ROOT}/web/my-react-app" && npm install
cd "${DESIGNBENCH_ROOT}/web/my-vue-app" && npm install
cd "${DESIGNBENCH_ROOT}/web/my-angular-app" && npm install

echo ""
echo "=== Patching metric_ast.py node path ==="
NODE_PATH=$(which node)
# macOS uses BSD sed (-i '' required); Linux uses GNU sed (-i alone works)
if [[ "$OSTYPE" == "darwin"* ]]; then
  sed -i '' "s|/Users/whalexiao/.nvm/versions/node/v18.19.0/bin/node|${NODE_PATH}|g" \
    "${DESIGNBENCH_ROOT}/code/evaluator/metric_ast.py"
else
  sed -i "s|/Users/whalexiao/.nvm/versions/node/v18.19.0/bin/node|${NODE_PATH}|g" \
    "${DESIGNBENCH_ROOT}/code/evaluator/metric_ast.py"
fi

echo ""
echo "=== Done ==="
echo "Run: python run_repair.py"
echo "  or: python run_repair.py --full"

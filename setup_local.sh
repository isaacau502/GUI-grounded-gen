#!/bin/bash
# One-time setup for running DesignBench repair locally
set -e

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
cd /home/isaacau/gui-g-gen/external/DesignBench
npm install @babel/parser @vue/compiler-dom parse5

echo ""
echo "=== Installing web app dependencies ==="
cd /home/isaacau/gui-g-gen/external/DesignBench/web/my-react-app && npm install
cd /home/isaacau/gui-g-gen/external/DesignBench/web/my-vue-app && npm install
cd /home/isaacau/gui-g-gen/external/DesignBench/web/my-angular-app && npm install

echo ""
echo "=== Patching metric_ast.py node path ==="
NODE_PATH=$(which node)
sed -i "s|/Users/whalexiao/.nvm/versions/node/v18.19.0/bin/node|${NODE_PATH}|g" \
  /home/isaacau/gui-g-gen/external/DesignBench/code/evaluator/metric_ast.py

echo ""
echo "=== Done ==="
echo "Run: python run_repair.py"
echo "  or: python run_repair.py --full"

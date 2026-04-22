# Site Render - Controle de Créditos

## Como funciona
Este site NÃO processa a planilha Excel.
Você processa o Excel no seu PC com o script local e sobe apenas o JSON pronto em /admin.

## Render
Build Command:
pip install -r requirements.txt

Start Command:
gunicorn app:app --timeout 120

## Variáveis de ambiente
ADMIN_PASSWORD=sua_senha
SECRET_KEY=sua_chave
DATA_DIR=/opt/render/project/src/data

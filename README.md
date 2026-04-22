# Controle de Créditos - versão corrigida para Render

## Correções aplicadas
- remove dependência de pandas para leitura do Excel
- usa openpyxl em modo read_only=True e data_only=True
- reduz consumo de memória na importação
- mantém painel público + administrador
- salva dados publicados em JSON

## Como subir no Render
Build Command:
pip install -r requirements.txt

Start Command:
gunicorn app:app --timeout 180

## Variáveis de ambiente recomendadas
ADMIN_PASSWORD=sua_senha_forte
SECRET_KEY=sua_chave_forte
DATA_DIR=/opt/render/project/src/data

## Python recomendado
Crie runtime.txt com:
python-3.12.7

# Controle de Créditos

## O que este sistema faz
- Painel público com dados já processados
- Área Administrador protegida por senha
- Upload da planilha apenas pelo administrador
- Dados ficam salvos até a próxima atualização
- Filtro exato por "NÃO REALIZADO"
- Ignora "EXAMES PAGOS E NÃO REALIZADOS ANTERIORMENTE"
- Agrupamento de créditos por recibo

## Como rodar localmente
1. Instale:
pip install -r requirements.txt

2. Execute:
python app.py

3. Acesse:
Painel: http://127.0.0.1:5000
Administrador: http://127.0.0.1:5000/admin/login

## Senha padrão do administrador
admin123

## Subir no Render
1. Crie um repositório no GitHub e envie todos os arquivos do projeto.
2. No Render, clique em New > Web Service.
3. Conecte sua conta do GitHub e escolha o repositório.
4. Preencha assim:
   - Language: Python 3
   - Build Command: pip install -r requirements.txt
   - Start Command: gunicorn app:app
5. Em Environment Variables, adicione:
   - ADMIN_PASSWORD = sua_senha_forte
   - SECRET_KEY = uma_chave_bem_grande
6. Clique em Create Web Service.
7. Quando terminar o deploy:
   - Painel público: sua-url.onrender.com
   - Administrador: sua-url.onrender.com/admin/login

## Observação importante sobre persistência no Render
Este sistema salva os dados processados em arquivos dentro da pasta data.
Em hospedagens sem armazenamento persistente, esses arquivos podem ser perdidos em reinícios ou novos deploys.
Para teste isso pode servir, mas para uso contínuo o ideal é usar:
- Persistent Disk no Render, ou
- banco de dados

## Comandos Git básicos
git init
git add .
git commit -m "Primeira versão"
git branch -M main
git remote add origin SEU_REPOSITORIO_GITHUB
git push -u origin main

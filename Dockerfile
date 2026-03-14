FROM mcr.microsoft.com/playwright:v1.40.0-jammy

# Instalar Python e pip
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/* \
    && ln -s /usr/bin/python3 /usr/bin/python

WORKDIR /app

# Copiar requirements e instalar dependências Python
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Copiar o resto do código
COPY . .

# Criar pastas necessárias
RUN mkdir -p temp_reports playwright_data

# Expor a porta do Streamlit
EXPOSE 8501

# Comando para rodar o app
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
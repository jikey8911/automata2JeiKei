FROM node:20-slim

WORKDIR /app

# Instalar pnpm
RUN npm install -g pnpm

# Copiar archivos de dependencias
COPY package.json pnpm-lock.yaml ./

# Copiar patches
COPY patches ./patches

# Instalar dependencias
RUN pnpm install --config.node-linker=hoisted

# Copiar el resto del código
COPY . .

# Exponer puertos (Vite/Node)
EXPOSE 3000

# Script de inicio (Modo Desarrollo por defecto)
CMD ["sh", "-c", "pnpm dev"]

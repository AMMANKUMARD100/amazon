# Dockerfile for React Vite Frontend
FROM node:20-alpine

WORKDIR /app

# Copy package list and install dependencies
COPY package.json ./
RUN npm install

# Copy source code
COPY . .

EXPOSE 3000

# Start Vite dev server on port 3000 with host binding
CMD ["npm", "run", "dev"]

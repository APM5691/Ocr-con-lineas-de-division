# This is the newer version

FROM node:22-alpine as builder

WORKDIR /app

COPY . .

RUN npm install

RUN npm i -g serve

RUN npm run build

EXPOSE 3000

CMD [ "serve", "-s", "dist" ]

# Production stage
FROM nginx:alpine

COPY --from=builder /app/dist /usr/share/nginx/html

COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
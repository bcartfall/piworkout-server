FROM node:alpine3.16

WORKDIR /app/frontend-react

# keep node_modules in docker container only
COPY package.json /app/frontend-react
COPY package-lock.json /app/frontend-react
COPY yarn.lock /app/frontend-react
RUN yarn install

EXPOSE 3000

CMD ["yarn", "run", "start"]
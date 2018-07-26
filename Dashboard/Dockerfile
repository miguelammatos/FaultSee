FROM node:12.8.1-stretch

# Create app directory
WORKDIR /usr/src/app

COPY package*.json ./
COPY jsconfig.json ./

RUN npm install

EXPOSE 3000
CMD [ "npm", "run", "start" ]


# Copy app

COPY public public

COPY src src


# CMD [ "node", "server.js" ]
# CMD [ "react-scripts", "build" ]
# CMD [ "tail", "-f", "/dev/null" ]

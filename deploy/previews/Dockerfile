FROM mcr.microsoft.com/playwright:v1.64.1-noble
WORKDIR /app
RUN npm init -y && npm install --omit=dev --ignore-scripts playwright-core@1.64.1
COPY --chown=pwuser:pwuser capture.mjs policy.mjs ./
USER pwuser
ENTRYPOINT ["node", "/app/capture.mjs"]

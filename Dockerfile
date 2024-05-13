FROM docker:26.1.2-cli-alpine3.19
RUN apk update
RUN apk add bash
RUN apk add python3
RUN apk add pipx
ENV PATH="/root/.local/bin:${PATH}"
RUN pipx ensurepath
RUN pipx install poetry
RUN mkdir /bot
WORKDIR /bot
ADD ./python_runner_bot /bot/python_runner_bot
ADD ./.env /bot/.env
ADD ./pyproject.toml /bot/pyproject.toml
RUN poetry install
CMD [ "poetry", "run", "bot" ]
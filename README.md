# AI COPILOTS

This is the FASTApi repository to connect to the genai workflow and have the copilot orchestration logic defined in one place.

## Run Locally

Clone the project

```sh
  git clone https://github.com/ishaan812/orbia.git
```

Go to the project directory

```sh
  cd orbia
```

Install dependencies

#### On Linux/Mac:

```sh
brew install poetry
```

#### On Windows:

```sh
pip install poetry
```

Next, run

```sh
poetry env activate
```
copy the output of the above command and paste and run in your terminal to activate the project's poetry env.

```sh
poetry install --no-root
```

To make sure psycopg runs on mac, do 

```sh
brew install libpq
```

and then add it to your path with the echo command shown in the terminal by brew.


#### Run project

```sh
uvicorn main:app --reload
```

## Set up pre-commit hook

```sh
pre-commit install
```

```sh
pre-commit run --all-files
```
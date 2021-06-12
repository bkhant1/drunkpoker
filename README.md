# Drinking poker

## Running locally

To start live reload of code for the [elm](https://elm-lang.org/) frontend:
```
npm install --global elm elm-live
cd drunkpoker/elm/frontend
elm-live --no-server --port 1234 --no-server src/Main.elm -- src/Main.elm --output=elm.js
```

To start the django development server:

```
python -m pip install -r requirements.txt
python manage.py runserver
```

The app will be available at http://localhost:8000

Players are automatically assigned an ID through cookies, for testing with more than one player, check out firefox [multi account containers](https://support.mozilla.org/en-US/kb/containers)

## Deployment

The app is hosted on [heroku](https://www.heroku.com
). See the [Procfile](Procfile) for deployment commands if you're looking to deploy somewhere else.

If auto-deploy is activated in heroku, any push to master will also automatically deploy. Otherwise, connect to heroku and trigger a manual deploy

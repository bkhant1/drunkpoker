port module Main exposing (..)

import Browser
import Html exposing (..)
import Html.Attributes exposing (..)
import Html.Events exposing (..)
import Http
import Json.Decode as D
import Json.Encode as Encode



-- MAIN

main : Program () Model Msg
main =
  Browser.element
    { init = init
    , view = view
    , update = update
    , subscriptions = subscriptions
    }


-- PORTS

port sendMessage : String -> Cmd msg
port messageReceiver : (String -> msg) -> Sub msg
port tableNameReceiver : (String -> msg) -> Sub msg



-- MODEL


type alias Model =
  { playerName : String
  , baseUrl : String
  , state: String
  }


init : () -> ( Model, Cmd Msg )
init flags =
  ( { state = "", playerName = "", baseUrl = "" }
  , Cmd.none
  )



-- UPDATE


type Msg
  = Recv String
  | Bet
  | TableName String
  | Discard (Result Http.Error ())


-- Use the `sendMessage` port when someone presses ENTER or clicks
-- the "Send" button. Check out index.html to see the corresponding
-- JS where this is piped into a WebSocket.
--
update : Msg -> Model -> ( Model, Cmd Msg )
update msg model =
    case msg of
        Recv message ->
            ( { model | state = message }
            , Cmd.none
            )
        Bet ->
            ( model
            , Http.post
                { url = model.baseUrl ++ "/actions/bet"
                , expect = Http.expectWhatever Discard
                , body = Http.jsonBody
                <| Encode.object
                    [ ("amount", Encode.int 42)
                    , ("player_name", Encode.string "Quentin")
                    , ("seat_number", Encode.string "3")
                    ]
                }
            )
        TableName tableName ->
            ( { model | baseUrl = "http://localhost:8000/table/" ++ tableName }
            , Cmd.none
            )
        Discard _ ->
            ( model
            , Cmd.none
            )


-- SUBSCRIPTIONS

-- Subscribe to the `messageReceiver` port to hear about messages coming in
-- from JS. Check out the index.html file to see how this is hooked up to a
-- WebSocket.
--
subscriptions : Model -> Sub Msg
subscriptions _ =
    Sub.batch
        [ messageReceiver Recv
        , tableNameReceiver TableName
        ]


-- VIEW

view : Model -> Html Msg
view model =
  div []
    [ h1 [] [ text "Poker" ]
    , div []
        [ button [ onClick Bet ] [ text "Bet" ]
        ]
    ]

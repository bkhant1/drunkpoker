port module Main exposing (..)

import Browser
import Dict exposing (Dict)
import Html
import Html.Styled.Attributes exposing (..)
import Html.Styled.Events exposing (..)
import Html.Styled exposing (Html, button, div, h1, img, input, text, toUnstyled)
import Http
import Json.Decode as D
import Json.Encode as Encode
import Css exposing (hex, px, rgb)
import Svg.Styled as Svg
import Svg.Styled.Attributes exposing (cx, cy, fill, rx, ry)


baseUrl: String
baseUrl = "https://obscure-shore-25002.herokuapp.com/"
--baseUrl= "http://localhost:1234/"


-- MAIN

main : Program () Model Msg
main =
  Browser.element
    { init = init
    , view = toUnstyled << view
    , update = update
    , subscriptions = subscriptions
    }


-- PORTS

port sendMessage : String -> Cmd msg
port messageReceiver : (String -> msg) -> Sub msg
port tableNameReceiver : (String -> msg) -> Sub msg



-- MODEL

type alias JsonState =
    { seats: Dict String String
    , players: Dict String JsonPlayer
    }


type alias JsonPlayer =
    { name: String
    , state: String
    , cards: Maybe (List Card)
    }


type alias SeatNumber = Int


type UiPlayerState =
    Iddle SeatNumber
    | Sitting SeatNumber
    | Playing SeatNumber
    | WaitingNextGame SeatNumber


type alias Card =
    { suit: String
    , value: Int
    }


type alias Player =
    { name: String
    , state: UiPlayerState
    , cards: Maybe (Card, Card)
    }


type alias GameState =
    { seats: Dict SeatNumber (Maybe Player)
    }


type alias Model =
  { playerName: String
  , baseUrl: String
  , gameState: GameState
  , playerState: UiPlayerState
  }


makeEmptySeat: SeatNumber -> (SeatNumber, Maybe Player)
makeEmptySeat seatNumber =
    (seatNumber, Nothing)

initWithObama =
    (
        { baseUrl = baseUrl ++ "table/abc"
        , gameState =
            { seats = Dict.fromList
                [(1,Just { name = "Hey", state=Playing }),(2,Just {name = "Hey", state=Playing}),(3,Just { name = "Hey", state=Playing }),(4,Nothing),(5,Just { name = "Hey", state=Playing }),(6,Nothing),(7,Nothing),(8,Nothing),(9,Nothing),(10,Nothing)] }
            , playerName = "Hey !"
            , playerState = Playing }
    , Http.post
        { url = baseUrl ++ "table/abc/actions/sit"
        , expect = Http.expectWhatever Discard
        , body = Http.jsonBody
            <| Encode.object
                [ ("player_name", Encode.string "Obama")
                , ("seat_number", Encode.int 1)
                ]
        }
    )
initFromBeforeSit =
    ( { baseUrl = baseUrl ++ "table/abc", gameState = { seats = Dict.fromList [(1,Nothing),(2,Nothing),(3,Nothing),(4,Nothing),(5,Nothing),(6,Nothing)] }, playerName = "Hello", playerState = Sitting 1 }
    , Cmd.none
    )
realInit =
    { gameState =
        { seats =
            Dict.fromList <| List.map makeEmptySeat <| List.range 1 6
        }
    , playerName = ""
    , baseUrl = ""
    , playerState = Iddle
    }

init : () -> ( Model, Cmd Msg )
init flags = initFromBeforeSit
  --( initWithObama
  --, Cmd.none
  --)



-- UPDATE


type Msg
  = Recv String
  | Bet
  | TableName String
  | Discard (Result Http.Error ())
  | EnterName SeatNumber
  | NameUpdate String
  | Sit Int


jsonStateDecoder: D.Decoder JsonState
jsonStateDecoder =
    D.map2 JsonState
        (D.field "seats" (D.dict D.string))
        (D.field "players"
            (D.dict
                (D.map3 JsonPlayer
                    (D.field "name" D.string)
                    (D.field "state" D.string)
                    (D.maybe (D.field "cards"
                        (D.list
                            (D.map2 Card
                                (D.index 1 D.string)
                                (D.index 0 D.int)
                            )
                        ))
                    )
                )
            )
        )


gameStateFromJsonState: JsonState -> GameState
gameStateFromJsonState jsonState =
    let
        seatsAsTuple = Dict.toList jsonState.seats
        stringStateToUiState stringState seatNumber =
            case stringState of
                "WAITING_NEW_GAME" -> WaitingNextGame seatNumber
                "MY_TURN" -> Playing seatNumber
                "IN_GAME" -> Playing seatNumber
                "FOLDED" -> Playing seatNumber
                _ -> Iddle seatNumber
        maybeTwoCardsFromCardsList list =
            case list of
                card1::card2::tail ->
                    Just (card1, card2)
                _ ->
                    Nothing
        jsonPlayerToPlayer jsonPlayer seatNumber =
            Player
                jsonPlayer.name
                (stringStateToUiState jsonPlayer.state seatNumber)
                (case jsonPlayer.cards of
                    Just cardList -> maybeTwoCardsFromCardsList cardList
                    Nothing -> Nothing
                )
        makePlayer playerId seatNumber =
            case Dict.get playerId jsonState.players of
                Nothing ->
                    Nothing
                Just jsonPlayer ->
                    Just (jsonPlayerToPlayer jsonPlayer seatNumber)
        stringSeatPlayerIdToSeatNumberPlayer (stringSeat, playerId) =
            let
                seatNumber =
                    case String.toInt stringSeat of
                        Just result -> result
                        Nothing -> Debug.log "Seat number in wrong format" -1
            in
            ( seatNumber
            , makePlayer playerId seatNumber
            )
    in
    GameState
        <| Dict.fromList
            <| List.map stringSeatPlayerIdToSeatNumberPlayer seatsAsTuple


update : Msg -> Model -> ( Model, Cmd Msg )
update msg model =
    case msg of
        Recv message ->
            case D.decodeString jsonStateDecoder message of
                Ok gameState -> Debug.log ("Decoded message: \n" ++ message ++ "\n to: \n"  ++ Debug.toString gameState) <|
                    ( { model | gameState = gameStateFromJsonState gameState }
                    , Cmd.none
                    )
                Err error ->
                    Debug.log ("I am fucking here bitch " ++ Debug.toString error)
                    ( model
                    , Cmd.none
                    )
        Bet ->
            ( model
            , Cmd.none
            )
        TableName tableName ->
            ( { model | baseUrl = baseUrl ++ "table/" ++ tableName }
            , Cmd.none
            )
        Discard _ ->
            ( model
            , Cmd.none
            )
        EnterName seatNumber ->
            ( { model | playerState = Sitting seatNumber }
            , Cmd.none
            )
        Sit seatNumber ->
            ( { model | playerState = Playing seatNumber }
            , Http.post
                  { url = model.baseUrl ++ "/actions/sit"
                  , expect = Http.expectWhatever Discard
                  , body = Http.jsonBody
                  <| Encode.object
                      [ ("player_name", Encode.string model.playerName)
                      , ("seat_number", Encode.int seatNumber)
                      ]
                  }
            )
        NameUpdate name ->
            ( { model | playerName = name }
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

theme =
    { cardWhite = rgb 255 255 255
    , cardRed = rgb 255  0 0
    , cardBlack = rgb 0 0 0
    , other = rgb 69 73 85
    , tableGreen = rgb 114 176 29
    , buttonBlue = rgb 77 189 219
    }


type alias Position =
    { pctTop: Float
    , pctLeft: Float
    }


sitButton: Position -> SeatNumber -> Html Msg
sitButton position seatNumber =
    button
        [ css
            [ Css.backgroundColor theme.buttonBlue
            , Css.width <| Css.pct 10
            , Css.height <| Css.pct 7
            , Css.position Css.absolute
            , Css.borderRadius <| Css.px 13
            , playerPositionCss position
            , Css.color theme.cardWhite
            , Css.fontSize <| Css.pct 160
            , Css.fontWeight Css.bold
            ]
        , onClick <| EnterName seatNumber
        ]
        [ text "SIT"]


playerPositionCss: Position -> Css.Style
playerPositionCss position =
    Css.batch
        [ Css.top (Css.pct position.pctTop)
        , Css.left (Css.pct position.pctLeft)
        , Css.position Css.absolute
        ]


ifIsEnter : msg -> D.Decoder msg
ifIsEnter msg =
    D.field "key" D.string
        |> D.andThen
            (\key -> if key == "Enter" then D.succeed msg else D.fail "some other key")


renderEmptySit: Model -> Position -> SeatNumber -> Html Msg
renderEmptySit model position seatNumber =
    case model.playerState of
        Iddle _ ->
            sitButton position seatNumber
        Sitting onSeat ->
            if onSeat == seatNumber then
                input
                    [ placeholder "Enter your name"
                    , css
                          [ Css.backgroundColor theme.buttonBlue
                          , Css.width <| Css.pct 10
                          , Css.height <| Css.pct 7
                          , Css.borderRadius <| Css.px 13
                          , playerPositionCss position
                          , Css.color theme.cardWhite
                          , Css.fontSize <| Css.pct 160
                          , Css.fontWeight Css.bold
                          ]
                    , on "keydown" (ifIsEnter <| Sit seatNumber)
                    , onInput NameUpdate
                    ]
                    []
            else
                sitButton position seatNumber
        Playing _ ->
            div [ css [ playerPositionCss position ] ] [ text "Empty seat" ]
        WaitingNextGame _ ->
            div [ css [ playerPositionCss position ] ] [ text "Empty seat" ]


cardToFilename: Card -> String
cardToFilename card =
    let
        suitCode =
            case card.suit of
                "HEART" -> "H"
                "DIAMONDS" -> "D"
                "SPADE" -> "S"
                "CLUBS" -> "C"
                x -> Debug.log ("Error, I don't know about suit " ++ x) "B"
        valueCode =
            if (card.value < 10) && (card.value > 1) then
                String.fromInt card.value
            else
                case card.value of
                    10 -> "T"
                    11 -> "J"
                    12 -> "Q"
                    13 -> "K"
                    14 -> "A"
                    x -> Debug.log ("Error, I don't know this card value " ++ String.fromInt x) "1"
    in
    valueCode ++ suitCode


renderPlayer: Player -> Position -> SeatNumber -> Html Msg
renderPlayer player position mySeatNumber =
    let
        cardProportion = 0.32
        cardHeight = 12
        cardsTop = Css.top (Css.vh 6)
        cardsLeft = 1.8
        cardsOffset = 1
        cardLeft1 = Css.left (Css.vw cardsLeft)
        cardLeft2 = Css.left (Css.vw (cardsLeft + cardsOffset))
        cardsSize =
            Css.batch
            [ Css.width (Css.vw <| cardProportion*cardHeight)
            , Css.height (Css.vh <| cardHeight)
            ]
        cardToUrl = \card -> baseUrl ++ "static/cards/" ++ cardToFilename card ++ ".svg"
        renderCard cardLeftPos url =
            div
                [ css
                    [ cardsSize
                    , Css.position Css.absolute
                    , cardLeftPos
                    , cardsTop
                    ]
                ]
                [ img
                    [ src url
                    , css
                         [ Css.height (Css.pct 100)
                         , Css.width (Css.pct 100)
                         ]
                    ]
                    []
                ]
        renderCards: Maybe (Card, Card) -> List (Html Msg)
        renderCards cards =
            case cards of
                Just (card1, card2) ->
                    [ renderCard cardLeft1 (cardToUrl card1)
                    , renderCard cardLeft2 (cardToUrl card2)
                    ]
                Nothing ->
                    case player.state of
                        Playing _ ->
                            [ renderCard cardLeft1 <| baseUrl ++ "static/cards/1B.svg"
                            , renderCard cardLeft2 <| baseUrl ++ "static/cards/1B.svg"
                            ]
                        _ ->
                            []
    in
    div
        [ css [ playerPositionCss position ] ]
        ([ div
            [ css
                [ Css.width (Css.vw 11)
                , Css.height (Css.vh 22)
                , Css.position Css.relative
                , Css.top (Css.vh -10)
                , Css.left (Css.vw -5)
                ]
            ]
            [ img
                 [ src <| baseUrl ++ "static/avatar" ++ String.fromInt mySeatNumber ++ ".png"
                 , css
                     [ Css.height (Css.pct 100)
                     , Css.width (Css.pct 100)
                     ]
                 ]
                 []
            ]
        ] ++ renderCards player.cards)


playerSit: Model -> Position -> SeatNumber -> Html Msg
playerSit model position seatNumber =
    case Dict.get seatNumber model.gameState.seats of
        Nothing ->
            renderEmptySit model position seatNumber
        Just Nothing ->
            renderEmptySit model position seatNumber
        Just (Just player) ->
            renderPlayer player position seatNumber


playerSits: Model -> List (Html Msg)
playerSits model =
    [ playerSit model { pctTop = 17, pctLeft = 45} 2
    , playerSit model { pctTop = 31, pctLeft = 10} 1
    , playerSit model { pctTop = 31, pctLeft = 80} 3
    , playerSit model { pctTop = 63, pctLeft = 10} 6
    , playerSit model { pctTop = 63, pctLeft = 80} 4
    , playerSit model { pctTop = 75, pctLeft = 45} 5
    ]


actions: Model -> List (Html Msg)
actions model =
    case model.playerState of
        Iddle _ -> []
        Sitting _ -> []
        Playing seatNumber -> []
        WaitingNextGame seatNumber -> []


view : Model -> Html Msg
view model =
  div [ css
            [ Css.zIndex <| Css.int 1
            , Css.backgroundColor theme.other
            , Css.flex Css.none
            , Css.width <| Css.pct 100
            , Css.height <| Css.pct 100
            ]
      ]
      (playerSits model ++

      [ div
            [ css
                [ Css.zIndex <| Css.int 2
                , Css.width <| Css.pct 100
                , Css.height <| Css.pct 100
                ]
            ]
            [ Svg.svg
                [ fill "#72b01dff"
                , Svg.Styled.Attributes.width "100%"
                , Svg.Styled.Attributes.height "100%"
                ]
                [ Svg.ellipse
                    [ cx "50%", cy "50%", rx "41%", ry "30%" ]
                    []
                ]
            ]
    ])

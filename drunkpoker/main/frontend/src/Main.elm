port module Main exposing (..)

import Browser
import Dict exposing (Dict)
import Html.Styled.Attributes exposing (..)
import Html.Styled.Events exposing (..)
import Html.Styled exposing (Html, button, div, img, input, text, toUnstyled)
import Http
import Json.Decode as D
import Json.Encode as Encode
import Css exposing (rgb)
import Svg.Styled as Svg
import Svg.Styled.Attributes exposing (cx, cy, fill, rx, ry)


-- elm-live --start-page=index.html src/Main.elm -- --output=elm.js --debug


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
    , gameState: String
    , flop: Maybe (List Card)
    }


type alias JsonPlayer =
    { name: String
    , state: String
    , cards: Maybe (List Card)
    , committedBy: Maybe Int
    }


type alias SeatNumber = Int


type SubState =
    MyTurn
    | InGame
    | Folded


type UiPlayerState =
    Iddle SeatNumber
    | Playing SeatNumber SubState
    | WaitingNextGame SeatNumber


type alias Card =
    { suit: String
    , value: Int
    }


type alias Player =
    { name: String
    , state: UiPlayerState
    , cards: Maybe (Card, Card)
    , committedBy: Maybe Int
    }


type EnumGameState =
    GameInProgress
    | GameOver


type alias GameState =
    { seats: Dict SeatNumber (Maybe Player)
    , gameState: EnumGameState
    , flop: Maybe (Card, Card, Card)
    }


type Seated =
    Not
    | PickingName SeatNumber
    | Seated SeatNumber


type alias Model =
  { playerName: String
  , baseUrl: String
  , hostName: String
  , gameState: GameState
  , seated: Seated
  }


getSeatNumber: Seated -> Maybe SeatNumber
getSeatNumber seated =
    case seated of
        Seated seatNo -> Just seatNo
        _ -> Nothing


getMePlayer: Model -> Maybe Player
getMePlayer model =
    let
        seatNumber = getSeatNumber model.seated
    in
    case seatNumber of
        Nothing ->
            Nothing
        Just theSeatNumber ->
            case Dict.get theSeatNumber model.gameState.seats of
                Just player ->
                    player
                _ ->
                    Nothing


makeEmptySeat: SeatNumber -> (SeatNumber, Maybe Player)
makeEmptySeat seatNumber =
    (seatNumber, Nothing)


realInit =
    ( { gameState =
        { seats =
            Dict.fromList <| List.map makeEmptySeat <| List.range 1 6
        , gameState = GameInProgress
        , flop = Nothing
        }
      , playerName = ""
      , baseUrl = ""
      , seated = Not
      , hostName = "?"
      }
    , Cmd.none
    )


init : () -> ( Model, Cmd Msg )
init _ = realInit


-- UPDATE


type Msg =
  Receive String
  | PrepareRaise
  | Fold
  | Check
  | Call
  | ShowCards
  | NextGame
  | TableName String
  | Discard (Result Http.Error ())
  | EnterName SeatNumber
  | NameUpdate String
  | Sit Int


getHostName: String -> String
getHostName url =
    case String.split "/" url of
        protocol::_::hostname::_ -> protocol ++ "//" ++ hostname
        _ -> ""


cardDecoder: D.Decoder Card
cardDecoder =
    (D.map2 Card
        (D.index 1 D.string)
        (D.index 0 D.int)
    )

jsonStateDecoder: D.Decoder JsonState
jsonStateDecoder =
    D.map4 JsonState
        (D.field "seats" (D.dict D.string))
        (D.field "players"
            (D.dict
                (D.map4 JsonPlayer
                    (D.field "name" D.string)
                    (D.field "state" D.string)
                    (D.maybe (D.field "cards"
                        (D.list cardDecoder))
                    )
                    (D.maybe (D.field "committed_by" D.int))
                )
            )
        )
        (D.field "game_state" D.string)
        (D.maybe (D.field "flop"
            (D.list cardDecoder)
        ))


gameStateFromJsonState: JsonState -> GameState
gameStateFromJsonState jsonState =
    let
        seatsAsTuple = Dict.toList jsonState.seats
        stringStateToUiState stringState seatNumber =
            case stringState of
                "WAITING_NEW_GAME" -> WaitingNextGame seatNumber
                "MY_TURN" -> Playing seatNumber MyTurn
                "IN_GAME" -> Playing seatNumber InGame
                "FOLDED" -> Playing seatNumber Folded
                _ -> Iddle seatNumber
        maybeTwoCardsFromCardsList list =
            case list of
                card1::card2::_ ->
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
                jsonPlayer.committedBy
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
        cards: Maybe (Card, Card, Card)
        cards =
            case jsonState.flop of
                Just (c1::c2::c3::_) ->
                    Just (c1, c2, c3)
                _ ->
                    Nothing
    in
    GameState
        (Dict.fromList (List.map stringSeatPlayerIdToSeatNumberPlayer seatsAsTuple))
        (case jsonState.gameState of
            "GAME_OVER" -> GameOver
            _ -> GameInProgress
        )
        cards


update : Msg -> Model -> ( Model, Cmd Msg )
update msg model = Debug.log "The state: " <|
    let
        postAction action =
            Http.post
              { url = model.baseUrl ++ "/actions/" ++ action
              , expect = Http.expectWhatever Discard
              , body = Http.jsonBody
              <| Encode.object
                  [ ("player_name", Encode.string model.playerName)
                  ]
              }
    in
    case msg of
        Receive message ->
            case D.decodeString jsonStateDecoder message of
                Ok gameState -> Debug.log ("Decoded message: \n" ++ message ++ "\n to: \n"  ++ Debug.toString gameState) <|
                    ( { model | gameState = gameStateFromJsonState gameState }
                    , Cmd.none
                    )
                Err error ->
                    Debug.log ("Error when decoding json state: " ++ Debug.toString error)
                    ( model
                    , Cmd.none
                    )
        PrepareRaise ->
            ( model
            , Cmd.none
            )
        Fold ->
            ( model
            , postAction "fold"
            )
        TableName baseUrl ->
            ( { model | baseUrl = baseUrl, hostName = getHostName baseUrl }
            , Cmd.none
            )
        Discard _ ->
            ( model
            , Cmd.none
            )
        EnterName seatNumber ->
            ( { model | seated = PickingName seatNumber }
            , Cmd.none
            )
        Sit seatNumber ->
            ( { model | seated = Seated seatNumber }
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
        ShowCards ->
            ( model
            , Cmd.none
            )
        NextGame ->
            ( model
            , postAction "nextGame"
            )
        Check ->
            ( model
            , postAction "check"
            )
        Call ->
            ( model
            , postAction "call"
            )


-- SUBSCRIPTIONS

-- Subscribe to the `messageReceiver` port to hear about messages coming in
-- from JS. Check out the index.html file to see how this is hooked up to a
-- WebSocket.
--
subscriptions : Model -> Sub Msg
subscriptions _ =
    Sub.batch
        [ messageReceiver Receive
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
    , buttonGrey = rgb 140 140 140
    , fontSizeButtons = Css.fontSize <| Css.pct 160
    , fontWeightButtons = Css.fontWeight Css.bold
    }


type alias Position =
    { pctTop: Float
    , pctLeft: Float
    }


interactCommonCss: Css.Style
interactCommonCss =
    Css.batch
        [ Css.backgroundColor theme.buttonBlue
        , Css.width <| Css.pct 10
        , Css.height <| Css.pct 7
        , Css.borderRadius <| Css.px 13
        , Css.position Css.absolute
        , Css.color theme.cardWhite
        , Css.fontSize <| Css.pct 160
        , Css.fontWeight Css.bold
        ]


sitButton: Position -> SeatNumber -> Html Msg
sitButton position seatNumber =
    button
        [ css
            [ interactCommonCss
            , playerPositionCss position
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
    case model.seated of
        Not ->
            sitButton position seatNumber
        PickingName onSeat ->
            if onSeat == seatNumber then
                input
                    [ placeholder "Enter your name"
                    , css
                          [ interactCommonCss
                          , playerPositionCss position
                          ]
                    , on "keydown" (ifIsEnter <| Sit seatNumber)
                    , onInput NameUpdate
                    ]
                    []
            else
                sitButton position seatNumber
        Seated _ ->
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


cardToUrl: Model -> Card -> String
cardToUrl model card = model.hostName ++ "/static/cards/" ++ cardToFilename card ++ ".svg"


renderCard cardTopVhPos cardLeftVwPos url =
    renderCardWithSize cardTopVhPos cardLeftVwPos 12 url


renderCardWithSize: Float -> Float -> Float -> String -> (Html Msg)
renderCardWithSize cardTopVhPos cardLeftVwPos size url =
    let
        cardsSize =
            let
                cardHeight = size
                cardProportion = 0.32
            in
            Css.batch
            [ Css.width (Css.vw <| cardProportion*cardHeight)
            , Css.height (Css.vh <| cardHeight)
            ]
    in
    div
        [ css
            [ cardsSize
            , Css.position Css.absolute
            , Css.left (Css.vw cardLeftVwPos)
            , Css.top (Css.vh cardTopVhPos)
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


renderPlayer: Model -> Player -> Position -> SeatNumber -> Html Msg
renderPlayer model player position mySeatNumber =
    let
        cardsTop = 6
        cardsLeft = 1.8
        cardsOffset = 1
        backCardUrl = model.hostName ++ "/static/cards/1B.svg"
        renderCards: Maybe (Card, Card) -> List (Html Msg)
        renderCards cards =
            case cards of
                Just (card1, card2) ->
                    [ renderCard cardsTop cardsLeft (cardToUrl model card1)
                    , renderCard cardsTop (cardsLeft + cardsOffset) (cardToUrl model card2)
                    ]
                Nothing ->
                    case player.state of
                        Playing _ _ ->
                            [ renderCard cardsTop cardsLeft backCardUrl
                            , renderCard cardsTop (cardsLeft + cardsOffset) backCardUrl
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
                , theme.fontSizeButtons
                , theme.fontWeightButtons
                , Css.color theme.cardWhite
                ]
            ]
            [ img
                 [ src <| model.hostName ++ "/static/avatar" ++ String.fromInt mySeatNumber ++ ".png"
                 , css
                     [ Css.height (Css.pct 100)
                     , Css.width (Css.pct 100)
                     ]
                 ]
                 []
            , text <| Maybe.withDefault "" (Maybe.map String.fromInt player.committedBy)
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
            renderPlayer model player position seatNumber


playerSits: Model -> List (Html Msg)
playerSits model =
    let
        offset: Position
        offset = { pctTop = -5, pctLeft = 0}
    in
    [ playerSit model { pctTop = 17 + offset.pctTop , pctLeft = 45 + offset.pctLeft } 2
    , playerSit model { pctTop = 31 + offset.pctTop , pctLeft = 10 + offset.pctLeft} 1
    , playerSit model { pctTop = 31 + offset.pctTop , pctLeft = 80 + offset.pctLeft} 3
    , playerSit model { pctTop = 63 + offset.pctTop , pctLeft = 10 + offset.pctLeft} 6
    , playerSit model { pctTop = 63 + offset.pctTop , pctLeft = 80 + offset.pctLeft} 4
    , playerSit model { pctTop = 75 + offset.pctTop , pctLeft = 45 + offset.pctLeft} 5
    ]


flop: Model -> List (Html Msg)
flop model =
    let
        offset = 4.5
        flopLeft = 37
        flopTop = 35
        size = 14
    in
    case model.gameState.flop of
        Just (c1, c2, c3) ->
            [ renderCardWithSize flopTop flopLeft size (cardToUrl model c1)
            , renderCardWithSize flopTop (flopLeft + offset) size (cardToUrl model c2)
            , renderCardWithSize flopTop (flopLeft + 2*offset) size (cardToUrl model c3)
            ]
        Nothing ->
            []


inGameActions: Model -> List (Html Msg)
inGameActions model =
    let
        position: Position
        position = { pctTop = 92, pctLeft = 69}
        shouldDisplayActions: Bool
        shouldDisplayActions =
            case model.seated of
                    Seated seatNumber ->
                        case Dict.get seatNumber model.gameState.seats of
                            Just (Just me) ->
                                case me.state of
                                    Playing _ MyTurn ->
                                        True
                                    _ ->
                                        False
                            _ ->
                                False
                    _ ->
                        False
        getCommittedByOrZero: Maybe Player -> Int
        getCommittedByOrZero player =
            case player of
                Just it ->
                    Maybe.withDefault 0 << .committedBy <| it
                Nothing ->
                    0
        maxBet: Int
        maxBet =
            Maybe.withDefault 0
                <| List.maximum
                <| List.map
                    (getCommittedByOrZero << Tuple.second)
                    (Dict.toList model.gameState.seats)
        hasToCall: Bool
        hasToCall =
             (getCommittedByOrZero <| getMePlayer model) < maxBet
        offsetLeft: Float -> Css.Style
        offsetLeft pctOffset =
            Css.batch
                [ Css.top (Css.pct position.pctTop)
                , Css.left (Css.pct <| pctOffset + position.pctLeft)
                , Css.position Css.absolute
                ]
    in
    if shouldDisplayActions then
        [ button
            [ css
                [ interactCommonCss
                , offsetLeft 0
                ]
            , onClick <| PrepareRaise
            ]
            [ text "RAISE"]
        , button
            [ css
                [ interactCommonCss
                , offsetLeft 10.1
                ]
            , onClick <| Fold
            ]
            [ text "FOLD"]
        , button
            [ css
                [ interactCommonCss
                , offsetLeft 20.2
                ]
            , onClick <| if hasToCall then Call else Check
            ]
            [ text <| if hasToCall then "CALL" else "CHECK" ]
        ]
    else
        []


gameOverActions: Model -> List (Html Msg)
gameOverActions model =
    let
        isCurrentPlayerWaitingForNewGame =
            case getMePlayer model of
                Just player ->
                    case player.state of
                        WaitingNextGame _ ->
                            False
                        _ ->
                            True
                Nothing ->
                    False
        position: Position
        position = { pctTop = 92, pctLeft = 69}
        shouldDisplayActions: Bool
        shouldDisplayActions =
            case model.gameState.gameState of
                GameInProgress -> False
                GameOver -> True
        offsetLeft pctOffset =
            Css.batch
                [ Css.top (Css.pct position.pctTop)
                , Css.left (Css.pct <| pctOffset + position.pctLeft)
                , Css.position Css.absolute
                ]
        buttonNextGame =
            button
                [ css
                    [ interactCommonCss
                    , offsetLeft 0
                    ]
                , onClick <| NextGame
                ]
                [ text "NEXT GAME"]
        buttonShowCards =
            button
                [ css
                    [ interactCommonCss
                    , offsetLeft 10.1
                    , Css.backgroundColor theme.buttonGrey
                    ]
                , onClick <| ShowCards
                , disabled True
                ]
                [ text "SHOW CARDS"]

    in
    if shouldDisplayActions then
        if isCurrentPlayerWaitingForNewGame then
            [ buttonNextGame, buttonShowCards ]
        else
            [ buttonShowCards ]
    else
        []


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
      (playerSits model
      ++ inGameActions model
      ++ gameOverActions model
      ++ flop model
      ++
      [ div
            [ css
                [ Css.zIndex <| Css.int 2
                , Css.width <| Css.pct 100
                , Css.height <| Css.pct 99.5
                ]
            ]
            [ Svg.svg
                [ fill "#72b01dff"
                , Svg.Styled.Attributes.width "100%"
                , Svg.Styled.Attributes.height "100%"
                ]
                [ Svg.ellipse
                    [ cx "50%", cy "45%", rx "41%", ry "30%" ]
                    []
                ]
            ]
    ])

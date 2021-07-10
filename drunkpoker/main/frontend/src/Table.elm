port module Table exposing (..)

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


-- elm-live --no-server --port 1234 --no-server src/Main.elm -- src/Main.elm --output=elm.js


-- PORTS

port connectSocket : String -> Cmd msg
port messageReceiver : (String -> msg) -> Sub msg


-- MODEL


type alias PlayerId = String


type alias Sip = Int


type alias JsonResults =
    { winners: List PlayerId
    , drinkers: Dict PlayerId Sip
    , scores: Dict PlayerId Int
    }


type alias JsonState =
    { seats: Dict String String
    , players: Dict String JsonPlayer
    , gameState: String
    , communityCards: Maybe (List Card)
    , results: Maybe JsonResults
    , stacks: Maybe (Dict String Int)
    }


type alias JsonPlayer =
    { name: String
    , state: String
    , cards: Maybe (List Card)
    , committedBy: Maybe Int
    , showingCards: Bool
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
    , showingCards: Bool
    , stack: Maybe Int
    }


type EnumGameState =
    GameInProgress
    | GameOver


type Score =
    StraightFlush
    | FourOfAKind
    | FullHouse
    | Flush
    | Straight
    | ThreeOfAKind
    | TwoPairs
    | Pair
    | HighCard


type alias Results =
    { winnerNames: List (String)
    , drinkerNamesAndSips: List ((String, Sip))
    , namesAndScores: List ((String, Score))
    }


type alias GameState =
    { seats: Dict SeatNumber (Maybe Player)
    , gameState: EnumGameState
    , flop: Maybe (Card, Card, Card)
    , river: Maybe (Card)
    , turn: Maybe (Card)
    , results: Maybe Results
    }


type Seated =
    Not
    | PickingName SeatNumber
    | Seated SeatNumber


type TableType =
    Drunk
    | Normal


type alias Model =
  { playerName: String
  , baseUrl: String
  , hostName: String
  , gameState: GameState
  , seated: Seated
  , preparingRaise: Maybe Int
  , tableType: TableType
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


realInit: String -> TableType -> ( Model, Cmd Msg )
realInit tableUrl tableType =
    ( { gameState =
        { seats =
            Dict.fromList <| List.map makeEmptySeat <| List.range 1 6
        , gameState = GameInProgress
        , flop = Nothing
        , river = Nothing
        , turn = Nothing
        , results = Nothing
        }
      , playerName = ""
      , baseUrl = tableUrl
      , seated = Not
      , hostName = getHostName tableUrl
      , preparingRaise = Nothing
      , tableType = tableType
      }
    , case getTableName tableUrl of
        Just tableName ->
            connectSocket <|
                "{\"tableName\":\""
                ++ tableName
                ++ "\",\"tableType\":\""
                ++ (if tableType == Drunk then "drinking" else "normal")
                ++ "\"}"
        Nothing ->
            Cmd.none
    )


init : String -> TableType -> ( Model, Cmd Msg )
init = realInit


-- UPDATE


type Msg =
  Receive String
  | PrepareRaise
  | Raise Int
  | UpdateRaiseAmount String
  | Fold
  | Check
  | Call
  | ShowCards
  | NextGame
  | Discard (Result Http.Error ())
  | EnterName SeatNumber
  | NameUpdate String
  | Sit Int


getCommittedByOrZero: Maybe Player -> Int
getCommittedByOrZero player =
    case player of
        Just it ->
            Maybe.withDefault 0 << .committedBy <| it
        Nothing ->
            0


maxBet: Model -> Int
maxBet model =
    Maybe.withDefault 0
        <| List.maximum
        <| List.map
            (getCommittedByOrZero << Tuple.second)
            (Dict.toList model.gameState.seats)


getHostName: String -> String
getHostName url =
    case String.split "/" url of
        protocol::_::hostname::_ -> protocol ++ "//" ++ hostname
        _ -> ""


getTableName: String -> Maybe String
getTableName =
    List.head << List.reverse << String.split "/"


cardDecoder: D.Decoder Card
cardDecoder =
    (D.map2 Card
        (D.index 1 D.string)
        (D.index 0 D.int)
    )

jsonStateDecoder: D.Decoder JsonState
jsonStateDecoder =
    D.map6 JsonState
        (D.field "seats" (D.dict D.string))
        (D.field "players"
            (D.dict
                (D.map5 JsonPlayer
                    (D.field "name" D.string)
                    (D.field "state" D.string)
                    (D.maybe (D.field "cards"
                        (D.list cardDecoder))
                    )
                    (D.maybe (D.field "committed_by" D.int))
                    (D.oneOf [D.field "show_cards" D.bool, D.succeed False])
                )
            )
        )
        (D.field "game_state" D.string)
        (D.maybe (D.field "community_cards"
            (D.list cardDecoder)
        ))
        (D.maybe (D.field "results"
            (D.map3 JsonResults
                (D.field "winners" (D.list D.string))
                (D.field "drinkers" (D.dict D.int))
                (D.field "scores" (D.dict (D.index 0 D.int)))
            )
        ))
        (D.maybe (D.field "players_stacks" (D.dict ( D.int))))


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
        jsonPlayerToPlayer jsonPlayer seatNumber playerId =
            Player
                jsonPlayer.name
                (stringStateToUiState jsonPlayer.state seatNumber)
                (case jsonPlayer.cards of
                    Just cardList -> maybeTwoCardsFromCardsList cardList
                    Nothing -> Nothing
                )
                jsonPlayer.committedBy
                jsonPlayer.showingCards
                (case jsonState.stacks of
                    Nothing -> Nothing
                    Just stacks ->
                        Dict.get playerId stacks)
        makePlayer playerId seatNumber =
            case Dict.get playerId jsonState.players of
                Nothing ->
                    Nothing
                Just jsonPlayer ->
                    Just (jsonPlayerToPlayer jsonPlayer seatNumber playerId)
        stringSeatPlayerIdToSeatNumberPlayer (stringSeat, playerId) =
            let
                seatNumber =
                    case String.toInt stringSeat of
                        Just result -> result
                        Nothing -> -1
            in
            ( seatNumber
            , makePlayer playerId seatNumber
            )
        flop: Maybe (Card, Card, Card)
        flop =
            case jsonState.communityCards of
                Just (c1::c2::c3::_) ->
                    Just (c1, c2, c3)
                _ ->
                    Nothing
        river: Maybe (Card)
        river =
            case jsonState.communityCards of
                Just (_::_::_::c4::_) ->
                    Just (c4)
                _ ->
                    Nothing
        turn: Maybe (Card)
        turn =
            case jsonState.communityCards of
                Just (_::_::_::_::c5::_) ->
                    Just (c5)
                _ ->
                    Nothing
        intEnumToCombination theInt =
            case theInt of
                0 -> HighCard
                1 -> Pair
                2 -> TwoPairs
                3 -> ThreeOfAKind
                4 -> Straight
                5 -> Flush
                6 -> FullHouse
                7 -> FourOfAKind
                8 -> StraightFlush
                _ -> HighCard
        idsToNames ids =
            case ids of
                id::tail ->
                     Maybe.withDefault []
                        (Maybe.map
                            (List.singleton << .name)
                            (Dict.get id jsonState.players))
                     ++ idsToNames tail
                [] -> []
        idsXToNamesX idsX =
            case idsX of
                (id, x)::tail ->
                    Maybe.withDefault
                        []
                        (Maybe.map
                            (List.singleton << (\name -> (name, x)) << .name)
                            (Dict.get id jsonState.players))
                    ++ idsXToNamesX tail
                [] -> []
        gameResults =
            case jsonState.results of
                Nothing -> Nothing
                Just theResults ->
                    Just <| Results
                        (theResults.winners)
                        (idsXToNamesX (Dict.toList theResults.drinkers))
                        ((List.map (Tuple.mapSecond intEnumToCombination)
                            (idsXToNamesX (Dict.toList theResults.scores))))
        playersStacks =
            case jsonState.stacks of
                Nothing -> Nothing
                Just it -> Just it
    in
    GameState
        (Dict.fromList (List.map stringSeatPlayerIdToSeatNumberPlayer seatsAsTuple))
        (case jsonState.gameState of
            "GAME_OVER" -> GameOver
            _ -> GameInProgress
        )
        flop
        river
        turn
        gameResults


update : Msg -> Model -> ( Model, Cmd Msg )
update msg model =
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
                Ok gameState ->
                    ( { model | gameState = gameStateFromJsonState gameState }
                    , Cmd.none
                    )
                Err error ->
                    Debug.log ("Error when decoding json state: " ++ Debug.toString error)
                    ( model
                    , Cmd.none
                    )
        PrepareRaise ->
            ( { model | preparingRaise = Just (minRaiseAmount model) }
            , Cmd.none
            )
        Fold ->
            ( model
            , postAction "fold"
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
            , postAction "showCards"
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
        Raise amount ->
            ( { model | preparingRaise = Nothing }
            , Http.post
                  { url = model.baseUrl ++ "/actions/raise"
                  , expect = Http.expectWhatever Discard
                  , body = Http.jsonBody
                  <| Encode.object
                      [ ("player_name", Encode.string model.playerName)
                      , ("amount", Encode.int amount)
                      ]
                  }
            )
        UpdateRaiseAmount amount ->
            ( { model | preparingRaise = Just (Maybe.withDefault (maxBet model) (String.toInt amount)) }
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
        [ messageReceiver Receive ]


-- VIEW

theme =
    { cardWhite = rgb 255 255 255
    , cardRed = rgb 255  0 0
    , cardBlack = rgb 0 0 0
    , other = rgb 217 217 217 -- rgb 69 73 85
    , tableGreen = rgb 114 176 29
    , tableShade = rgb 72 112 18
    , buttonBlue = rgb 77 189 219
    , buttonGrey = rgb 140 140 140
    , fontSizeButtons = Css.fontSize <| Css.vw 2.1
    , fontSizePlayerDisplay = Css.fontSize <| Css.vw 1.8
    , fontWeightButtons = Css.fontWeight Css.bold
    }


type alias Position =
    { pctTop: Float
    , pctLeft: Float
    }


offsetPosition: Position -> (Float, Float) -> Position
offsetPosition {pctTop, pctLeft} (offsetTop, offsetLeft) =
    Position (pctTop + offsetTop) (pctLeft + offsetLeft)


interactCommonCss: Css.Style
interactCommonCss =
    Css.batch
        [ Css.backgroundColor theme.buttonBlue
        , Css.width <| Css.vw 10
        , Css.height <| Css.vh 7
        , Css.borderRadius <| Css.px 13
        , Css.position Css.absolute
        , Css.color theme.cardWhite
        , theme.fontSizeButtons
        , Css.fontWeight Css.bold
        ]


disabledInteractCommonCss =
    Css.batch
        [ interactCommonCss
        , Css.backgroundColor theme.buttonGrey
        ]


sitButton: Position -> SeatNumber -> Html Msg
sitButton position seatNumber =
    button
        [ css
            [ interactCommonCss
            , playerPositionCss position
            , Css.width <| Css.pct 12
            , Css.height <| Css.pct 6.5
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
                          , Css.width <| Css.pct 12
                          , Css.height <| Css.pct 6.5
                          ]
                    , on "keydown" (ifIsEnter <| Sit seatNumber)
                    , onInput NameUpdate
                    ]
                    []
            else
                sitButton position seatNumber
        Seated _ ->
            div [ css [ playerPositionCss position ] ] [ ]


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


renderPlayerCard cardTopPctPos cardLeftPctPos url =
    renderCardWithSize cardTopPctPos cardLeftPctPos 1 url


renderCardWithSize: Float -> Float -> Float -> String -> (Html Msg)
renderCardWithSize cardTopPctPos cardLeftPctPos size url =
    let
        cardsSize =
            Css.batch
                [ Css.width (Css.pct <| 41*size)
                , Css.height (Css.pct <| 111.1*size)
                , Css.zIndex <| Css.int 1
                ]
    in
    div
        [ css
            [ cardsSize
            , Css.position Css.absolute
            , Css.left (Css.pct cardLeftPctPos)
            , Css.top (Css.pct cardTopPctPos)
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
        avatarOffset: (Float, Float)
        avatarOffset =
            case mySeatNumber of
                1 -> (-8,4)
                2 -> (-7,4)
                3 -> (-7,4)
                4 -> (0,4)
                5 -> (1,4)
                6 -> (0,4)
                _ -> (0,0)
        cardsTop = 60
        cardsLeft = 20
        cardsOffset = 10.5
        backCardUrl = model.hostName ++ "/static/cards/1B.svg"
        font = Css.batch
            [ theme.fontSizePlayerDisplay
            , theme.fontWeightButtons
            , Css.color theme.cardWhite
            ]
        getStack =
            case model.tableType of
                Drunk -> player.committedBy
                Normal -> Maybe.map2 (-) player.stack player.committedBy
        getCommittedBy =
            case model.tableType of
                Drunk -> Nothing
                Normal -> player.committedBy
        renderGlow =
            case player.state of
                Playing _ MyTurn ->
                    [ div
                        [ css
                            [ Css.width <| Css.pct 40
                            , Css.height <| Css.pct 80
                            , Css.boxShadow5 (Css.vw 0) (Css.vh 0) (Css.px 40) (Css.vw 3) (Css.hex "FFFA00")
                            , Css.borderRadius <| Css.pct 40
                            , Css.border <| Css.px 0
                            , Css.top <| Css.pct -50
                            , Css.left <| Css.pct -12.5
                            , Css.position Css.absolute
                            , Css.zIndex (Css.int -1)
                            ]
                        ]
                        []
                    ]
                _ -> []
        renderStack =
            [ div
                [ css
                    [ font ]
                ]
                [ text <| Maybe.withDefault "" (Maybe.map String.fromInt getStack) ]
            ]
        renderCommittedBy =
            let committedByText = Maybe.withDefault "" (Maybe.map String.fromInt getCommittedBy) in
            [ div
                [ css
                    [ font ]
                ]
                [ text <| if committedByText /= "0" then committedByText else "" ]
            ]
        renderName: List (Html Msg)
        renderName =
            [ div
                [ css
                    [ font ]
                ]
                [ text <| String.left 8 player.name ]
            ]
        renderStackNameAndCommittedBy =
            [ div
                [ css
                  [ Css.height <| Css.pct 92
                  , Css.width <| Css.pct 100
                  , Css.backgroundColor <| theme.tableShade
                  , Css.padding4 (Css.px 4) (Css.px 0) (Css.px 0) (Css.px 6)
                  , Css.opacity <| Css.num 0.8
                  , Css.border3 (Css.px 0) Css.solid (Css.rgb 11 14 17)
                  , Css.borderRadius <| Css.px 5
                  , Css.position Css.absolute
                  , Css.top <| Css.pct 135.5
                  , Css.left <| Css.pct -33.6
                  , Css.zIndex <| Css.int -1
                  ]
                ]
                <| renderCommittedBy ++ renderStack ++ renderName
            ]
        renderCards: Maybe (Card, Card) -> List (Html Msg)
        renderCards cards =
            case cards of
                Just (card1, card2) ->
                    [ renderPlayerCard cardsTop cardsLeft (cardToUrl model card1)
                    , renderPlayerCard cardsTop (cardsLeft + cardsOffset) (cardToUrl model card2)
                    ]
                Nothing ->
                    case player.state of
                        Playing _ _ ->
                            [ renderPlayerCard cardsTop cardsLeft backCardUrl
                            , renderPlayerCard cardsTop (cardsLeft + cardsOffset) backCardUrl
                            ]
                        _ ->
                            []
    in
    div
        [ css
            [ playerPositionCss <| offsetPosition position avatarOffset
            , Css.width <| Css.pct 10
            , Css.height <| Css.pct 10
            , Css.zIndex (Css.int 1)
            ]
        ]
        ([ div
            [ css
                [ Css.width (Css.pct <| 12.5*10)
                , Css.height (Css.pct <| 23*10)
                , Css.position Css.relative
                , Css.top (Css.pct <| -100)
                , Css.left (Css.pct <| -55)
                ]
            ]
            [ img
                 [ src <| model.hostName ++ "/static/avatar" ++ String.fromInt mySeatNumber ++ ".png"
                 , css
                     [ Css.height (Css.pct 100)
                     , Css.width (Css.pct 100)
                     , Css.zIndex <| Css.int -2
                     ]
                 ]
                 []
            ]
        ]
        ++ renderGlow
        ++ renderCards player.cards
        ++ renderStackNameAndCommittedBy
        )


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
        offset = { pctTop = 0, pctLeft = 0}
    in
    [ playerSit model { pctTop = 17 + offset.pctTop , pctLeft = 45 + offset.pctLeft } 2
    , playerSit model { pctTop = 31 + offset.pctTop , pctLeft = 10 + offset.pctLeft } 1
    , playerSit model { pctTop = 31 + offset.pctTop , pctLeft = 80 + offset.pctLeft } 3
    , playerSit model { pctTop = 63 + offset.pctTop , pctLeft = 10 + offset.pctLeft } 6
    , playerSit model { pctTop = 63 + offset.pctTop , pctLeft = 80 + offset.pctLeft } 4
    , playerSit model { pctTop = 75 + offset.pctTop , pctLeft = 45 + offset.pctLeft } 5
    ]


pot: Model -> List (Html Msg)
pot model =
    let
        thePot = 1
        shouldDisplay = model.tableType == Normal
    in
    [ div
        [ css
            [ Css.position Css.absolute
            , Css.left (Css.vw 45)
            , Css.top (Css.vh 54)
            , theme.fontSizeButtons
            , theme.fontWeightButtons
            , Css.color theme.cardWhite
            ]
        ]
        [ text <| if thePot > 0 && shouldDisplay then "Pot: " ++ String.fromInt thePot else "" ]
    ]


communityCards: Model -> List (Html Msg)
communityCards model =
    let
        offset = 5.2
        flopLeft = 37
        flopTop = 41
        size = 0.125
        flopCards =
            case model.gameState.flop of
                Just (c1, c2, c3) ->
                    [ renderCardWithSize flopTop flopLeft size (cardToUrl model c1)
                    , renderCardWithSize flopTop (flopLeft + offset) size (cardToUrl model c2)
                    , renderCardWithSize flopTop (flopLeft + 2*offset) size (cardToUrl model c3)
                    ]
                Nothing ->
                    []
        riverCards =
            case model.gameState.river of
                Just (card) ->
                    [ renderCardWithSize flopTop (flopLeft + 3*offset) size (cardToUrl model card)
                    ]
                Nothing ->
                    []
        turnCards =
            case model.gameState.turn of
                Just (card) ->
                    [ renderCardWithSize flopTop (flopLeft + 4*offset) size (cardToUrl model card)
                    ]
                Nothing ->
                    []
    in
    flopCards ++ riverCards ++ turnCards


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
        hasToCall: Bool
        hasToCall =
             (getCommittedByOrZero <| getMePlayer model) < maxBet model
        offsetLeft: Float -> Css.Style
        offsetLeft pctOffset =
            Css.batch
                [ Css.top (Css.pct position.pctTop)
                , Css.left (Css.pct <| pctOffset + position.pctLeft)
                , Css.position Css.absolute
                ]
        isPreparingRaise =
            case model.preparingRaise of
                Nothing -> False
                Just _ -> True
        commonCss =
            if isPreparingRaise then disabledInteractCommonCss else interactCommonCss
        raiseAmount =
            Maybe.withDefault -1 model.preparingRaise
    in
    if shouldDisplayActions then
        [ button
            [ css
                [ interactCommonCss
                , offsetLeft 0
                ]
            , onClick <| if isPreparingRaise then Raise raiseAmount else PrepareRaise
            ]
            [ text (if isPreparingRaise then "OK" else "RAISE") ]
        , button
            [ css
                [ commonCss
                , offsetLeft 10.1
                ]
            , onClick <| Fold
            , disabled isPreparingRaise
            ]
            [ text "FOLD"]
        , button
            [ css
                [ commonCss
                , offsetLeft 20.2
                ]
            , onClick <| if hasToCall then Call else Check
            , disabled isPreparingRaise
            ]
            [ text <| if hasToCall then "CALL" else "CHECK" ]
        ]
    else
        []


gameOverActions: Model -> List (Html Msg)
gameOverActions model =
    let
        showCardsDisabled =
            case getMePlayer model of
                Just player ->
                    player.showingCards
                Nothing -> False
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
                    , Css.backgroundColor
                        (if showCardsDisabled then theme.buttonGrey else theme.buttonBlue)
                    ]
                , onClick <| ShowCards
                , disabled showCardsDisabled
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


minRaiseAmount: Model -> Int
minRaiseAmount model =
    case model.tableType of
        Drunk -> maxBet model
        Normal -> if maxBet model == 20 then 30 else 10


raiseSlider: Model -> List (Html Msg)
raiseSlider model =
    let
        sliderThumbWidth = 6
        sliderThumbHeight = 3.3
        positionTop = 85
        positionLeft = 69
        textLeftOffset = 9.5
        textTopOffset = -8
        sliderStyle =
            let
                sliderThumbStyleFirefox =
                    Css.batch
                        [ Css.width (Css.pct sliderThumbWidth)
                        , Css.borderRadius (Css.em 2)
                        , Css.height (Css.vh sliderThumbHeight)
                        , Css.backgroundColor theme.buttonBlue
                        ]
                sliderThumbStyleChrome =
                    Css.batch
                        [ Css.width (Css.pct sliderThumbWidth)
                        , Css.borderRadius (Css.em 2)
                        , Css.height (Css.vh sliderThumbHeight)
                        , Css.property "background" theme.buttonBlue.value
                        ]
            in
            Css.batch
                [ Css.property "-webkit-appearance" "none"
                , Css.backgroundColor theme.cardWhite
                , Css.width (Css.pct 30)
                , Css.height (Css.pct 3)
                , Css.borderRadius (Css.em 2)
                , Css.pseudoElement
                     "-moz-range-thumb"
                     [ Css.property "-moz-appearance" "none"
                     , sliderThumbStyleFirefox
                     ]
                , Css.pseudoElement
                    "-webkit-slider-thumb"
                    [ Css.property "-webkit-appearance" "none"
                    , Css.property "appearance" "none"
                    , sliderThumbStyleChrome
                    ]
                ]
        maxAmount =
            if model.tableType == Drunk then
                20
            else
                case getMePlayer model of
                    Just player ->
                        Maybe.withDefault 0 <| Maybe.map2 (-) player.stack player.committedBy
                    Nothing ->
                        0
        amount = Maybe.withDefault (minRaiseAmount model) model.preparingRaise
        sliderStep = if model.tableType == Drunk then 1 else 10
        stringAmount = String.fromInt <| amount
        textStyle =
            Css.batch
                [ Css.color theme.cardWhite
                , Css.fontSize <| Css.pct 160
                , Css.fontWeight Css.bold
                , Css.textAlign Css.right
                , Css.width (Css.pct 20)
                ]
        shouldDisplay =
            case model.preparingRaise of
                Just _ -> True
                Nothing -> False
    in
    if shouldDisplay then
        [ input
          [ css
            [ Css.position Css.absolute
            , Css.top (Css.pct positionTop)
            , Css.left (Css.pct positionLeft)
            , sliderStyle
            ]
          , type_ "range"
          , Html.Styled.Attributes.step (String.fromInt <| sliderStep)
          , Html.Styled.Attributes.min (String.fromInt <| minRaiseAmount model)
          , Html.Styled.Attributes.max <| String.fromInt maxAmount
          , value stringAmount
          , onInput UpdateRaiseAmount
          ] []
        , Html.Styled.p
            [ css
                [ Css.position Css.absolute
                , Css.top (Css.pct <| positionTop + textTopOffset)
                , Css.left (Css.pct <| positionLeft + textLeftOffset)
                , textStyle
                ]
            ]
            [ text (if amount /= maxAmount then stringAmount else "ALL IN !") ]
        ]
    else
        []


results: Model -> List (Html Msg)
results model =
    []


view : Model -> Int -> Int -> Html Msg
view model windowWidth windowHeight =
    div
        [ css
            [ Css.backgroundColor theme.other
            , Css.height <| Css.pct 100
            , Css.width <| Css.pct 100
            , Css.displayFlex
            ]
        ]
        [viewApp model windowWidth windowHeight]


viewApp : Model -> Int -> Int -> Html Msg
viewApp model windowWidth windowHeight =
  let
      appRatioLegacy = 0.5
      appRatio = appRatioLegacy
      (wwf, whf) = (toFloat windowWidth, toFloat windowHeight)
      windowRatio = (whf/wwf)
      (appWidth, appHeight) =
          if windowRatio > appRatio then
              (wwf, wwf*appRatio)
          else
              (whf/appRatio, whf)
  in
  div [ css
            [ Css.zIndex <| Css.int 1
            , Css.backgroundColor theme.other
            , Css.width <| Css.px appWidth
            , Css.height <| Css.px appHeight
            , Css.position Css.relative
            , Css.margin Css.auto
            ]
      ]
      (playerSits model
      ++ inGameActions model
      ++ gameOverActions model
      ++ communityCards model
      ++ pot model
      ++ results model
      ++ raiseSlider model
      ++
      [ div
            [ css
                [ Css.zIndex <| Css.int 2
                , Css.width <| Css.pct 100
                , Css.height <| Css.pct 99.5
                ]
            ]
            [ Svg.svg
                [ Svg.Styled.Attributes.width "100%"
                , Svg.Styled.Attributes.height "100%"
                ]
                [ Svg.ellipse
                    [ fill "#3d330cff", cx "50%", cy "50.5%", rx "43.5%", ry "32.5%" ]
                    []
                , Svg.ellipse
                    [ fill "#72b01dff", cx "50%", cy "50%", rx "41%", ry "30%" ]
                    []
                ]
            ]
      ])

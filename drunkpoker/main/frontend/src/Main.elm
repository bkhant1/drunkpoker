module Main exposing (..)

import Html.Styled.Attributes exposing (..)
import Html.Styled.Events exposing (..)
import Browser
import Table exposing (theme, interactCommonCss, ifIsEnter, TableType(..))
import Browser.Navigation as Navigation
import Browser.Events
import Url
import Url.Builder
import Html.Styled as Html exposing (Html, li, div, img, input, text, toUnstyled, ul)
import Url.Parser as UP exposing ((</>), s)
import Css
import Maybe exposing (withDefault)


main : Program (List Int) Model Msg
main =
  Browser.application
    { init = init
    , view = \model ->
        let
            theView = (Html.toUnstyled << view) model
        in
        Browser.Document "Hey" [theView]
    , update = update
    , subscriptions = subscriptions
    , onUrlChange = SomeUrlRequest
    , onUrlRequest = SomeUrlChange
    }


type alias WindowSize =
    { width: Int
    , height: Int
    }


type Msg
    = TableMsg Table.Msg
    | SomeUrlChange Browser.UrlRequest
    | SomeUrlRequest Url.Url
    | DrunkTableNameUpdate String
    | GoToDrunkTable
    | NormalTableNameUpdate String
    | GoToNormalTable
    | WindowSizeChanged Int Int


type alias Model =
    { table: Table.Model
    , route: Maybe TableType
    , key: Navigation.Key
    , drunkTableName: String
    , normalTableName: String
    , homeUrl: String
    , windowSize: WindowSize
    }


maybeSquarred: Maybe (Maybe a) -> Maybe a
maybeSquarred maybeIt =
    case maybeIt of
        Just it ->
            it
        Nothing ->
            Nothing


init : List Int -> Url.Url -> Navigation.Key -> (Model, Cmd Msg)
init wSize url key =
    let
        tableKey = maybeSquarred <| UP.parse routeParser <| Debug.log "Url: " url
        (tableModel, tableCmd) = Table.init (Url.toString url) (withDefault Drunk tableKey)
        (width, height) =
            case wSize of
                (w::h::_) -> (w, h)
                _ -> (0, 0)
    in
    ( Model
        tableModel
        tableKey
        key
        ""
        ""
        (Url.toString url)
        (WindowSize width height)
    , Cmd.batch
        [Cmd.map TableMsg tableCmd]
    )


routeParser : UP.Parser (Maybe TableType -> a) a
routeParser =
  UP.oneOf
    [ UP.map (always <| Just Drunk) (s "drinkingtable" </> UP.string)
    , UP.map (always <| Just Normal) (s "normaltable" </> UP.string)
    , UP.map Nothing (s "")
    ]


view : Model -> Html.Html Msg
view model =
    case model.route of
        Just Drunk ->
            Html.map TableMsg (Table.view model.table model.windowSize.width model.windowSize.height)
        Just Normal ->
            Html.map TableMsg (Table.view model.table model.windowSize.width model.windowSize.height)
        Nothing ->
            homepageView model


homepageView : Model -> Html.Html Msg
homepageView model =
    let
        introText theText fontSize =
            div
                [ css
                    [ Css.color theme.cardWhite
                    , Css.fontSize <| Css.pct fontSize
                    , Css.fontWeight Css.bold
                    , Css.padding <| Css.pct 1
                    ]
                ]
                [ text theText ]
    in
    div
        [ css
            [ Css.zIndex <| Css.int 1
            , Css.backgroundColor theme.other
            , Css.flex Css.none
            , Css.width <| Css.pct 100
            , Css.height <| Css.pct 100
            ]
        ]
        [ div
            [ css
                [ Css.zIndex <| Css.int 1
                , Css.backgroundColor theme.tableGreen
                , Css.flex Css.none
                , Css.position Css.absolute
                , Css.left <| Css.pct 30
                , Css.width <| Css.pct 70
                , Css.height <| Css.pct 100
                ]
            ]
            [ introText "Welcome to drunkpoker.com!" 400
            , introText """You can play classic poker or drinking poker.
                    To start, just enter a table name to join - or create - a poker game."""  200
            , introText "Here are the rules of drinking poker:"  200
            , ul
                [ css
                    [ Css.listStyle Css.none
                    ]
                ]
                [ li
                    [ css
                        [ Css.before
                            [ Css.color theme.cardRed
                            , Css.property "content" "•"
                            ]
                        ]
                    ]
                    [ introText "Rule 1" 100
                    ]
                , li
                    [ css
                        [ Css.before
                            [ Css.color theme.cardRed
                            , Css.paddingRight <| Css.px 8
                            , Css.property "content" "•"
                            ]
                        ]
                    ]
                    [ introText "Rule 2" 100
                    ]
                ]
            ]
        , div
            [ css
                [ Css.position Css.absolute
                , Css.top (Css.pct 4)
                , Css.left (Css.pct 0)
                , Css.width <| Css.pct 30
                , Css.height <| Css.pct 30
                ]
            ]
            [ introText "Join or create a drinking poker table:" 200
            , input
                [ placeholder "Table name"
                , css
                    [ interactCommonCss
                    , Css.width <| Css.pct 90
                    , Css.height <| Css.pct 20
                    , Css.top (Css.pct 50)
                    , Css.left (Css.pct 1)
                    ]
                , on "keydown" (ifIsEnter <| GoToDrunkTable)
                , onInput DrunkTableNameUpdate
                ]
                []
            ]
        ,div
             [ css
                 [ Css.position Css.absolute
                 , Css.top (Css.pct 30)
                 , Css.left (Css.pct 0)
                 , Css.width <| Css.pct 30
                 , Css.height <| Css.pct 30
                 ]
             ]
             [ introText "Join or create a normal poker table:" 200
             , input
                 [ placeholder "Table name"
                 , css
                     [ interactCommonCss
                     , Css.width <| Css.pct 90
                     , Css.height <| Css.pct 20
                     , Css.top (Css.pct 50)
                     , Css.left (Css.pct 1)
                     ]
                 , on "keydown" (ifIsEnter <| GoToNormalTable)
                 , onInput NormalTableNameUpdate
                 ]
                 []
             ]
        ]


update: Msg -> Model -> (Model, Cmd Msg)
update msg model =
    let
        goToTable tableType =
            let
                tableName = if tableType == "normal" then model.normalTableName else model.drunkTableName
                (tableModel, tableCmd) =
                    Table.init
                        (model.homeUrl ++ tableType ++ "table/" ++ tableName)
                        (if tableType == "normal" then Normal else Drunk)
            in
            ( { model | table = tableModel }
            , Cmd.batch
                [ Navigation.pushUrl
                    model.key
                    <| Url.Builder.absolute [tableType ++ "table", tableName] []
                , Cmd.map TableMsg tableCmd
                ]
            )
    in
    case msg of
        TableMsg it ->
            let
                (tableModel, theCmd) = Table.update it model.table
            in
            ({ model | table = tableModel }, Cmd.batch [Cmd.map TableMsg <| theCmd])
        SomeUrlChange urlRequest ->
            case urlRequest of
                Browser.Internal url ->
                    ({ model | route = maybeSquarred <| UP.parse routeParser url }, Navigation.pushUrl model.key (Url.toString url))
                Browser.External url ->
                    (model, Cmd.none)
        SomeUrlRequest url ->
            ({ model | route = maybeSquarred <| UP.parse routeParser url }, Cmd.none)
        DrunkTableNameUpdate name ->
            ({ model | drunkTableName = name }, Cmd.none)
        NormalTableNameUpdate name ->
            ({ model | normalTableName = name }, Cmd.none)
        GoToDrunkTable ->
            goToTable "drinking"
        GoToNormalTable ->
            goToTable "normal"
        WindowSizeChanged w h ->
            ( { model | windowSize = WindowSize w h }
            , Cmd.none
            )


subscriptions : Model -> Sub Msg
subscriptions model =
    Sub.batch
        [ Sub.map TableMsg (Table.subscriptions model.table)
        , Browser.Events.onResize (\w h -> WindowSizeChanged w h)
        ]

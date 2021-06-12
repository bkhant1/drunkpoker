module Main exposing (..)

import Html.Styled.Attributes exposing (..)
import Html.Styled.Events exposing (..)
import Browser
import Table exposing (theme, interactCommonCss, ifIsEnter, TableType(..))
import Browser.Navigation as Navigation
import Url
import Url.Builder
import Html.Styled as Html exposing (Html, li, div, img, input, text, toUnstyled, ul)
import Url.Parser as UP exposing ((</>), s)
import Css
import Maybe exposing (withDefault)


main : Program () Model Msg
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


type Msg
    = TableMsg Table.Msg
    | SomeUrlChange Browser.UrlRequest
    | SomeUrlRequest Url.Url
    | DrunkTableNameUpdate String
    | GoToDrunkTable
    | NormalTableNameUpdate String
    | GoToNormalTable


type alias Model =
    { table: Table.Model
    , route: Maybe TableType
    , key: Navigation.Key
    , drunkTableName: String
    , normalTableName: String
    , homeUrl: String
    }


maybeSquarred: Maybe (Maybe a) -> Maybe a
maybeSquarred maybeIt =
    case maybeIt of
        Just it ->
            it
        Nothing ->
            Nothing


init : () -> Url.Url -> Navigation.Key -> (Model, Cmd Msg)
init _ url key =
    let
        tableKey = maybeSquarred <| Debug.log "The url :" <| UP.parse routeParser url
        (tableModel, theCmd) = Table.init (Url.toString url) (withDefault Drunk tableKey)
    in
    ( Model
        tableModel
        tableKey
        key
        ""
        ""
        (Url.toString url)
    , Cmd.batch
        [Cmd.map TableMsg theCmd]
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
    case Debug.log "The route: " model.route of
        Just Drunk ->
            Html.map TableMsg (Table.view model.table)
        Just Normal ->
            Html.map TableMsg (Table.view model.table)
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
                (tableModel, tableCmd) =
                    Table.init
                        (model.homeUrl ++ tableType ++ "table/" ++ model.drunkTableName)
                        (withDefault Drunk model.route)
            in
            ( { model | table = tableModel }
            , Cmd.batch
                [ Navigation.pushUrl
                    model.key
                    <| Url.Builder.absolute [tableType ++ "table", model.drunkTableName] []
                , Cmd.map TableMsg tableCmd
                ]
            )
    in
    case msg of
        TableMsg it ->
            let
                (tableModel, theCmd) = Table.update it model.table
            in
            ({ model | table = tableModel }, Cmd.batch [Cmd.map TableMsg <| Debug.log "cmd: " theCmd])
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


subscriptions : Model -> Sub Msg
subscriptions model =
    Sub.map TableMsg (Table.subscriptions model.table)

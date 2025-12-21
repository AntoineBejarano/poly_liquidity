En Polymarket existe una jerarquía clara que debe respetarse estrictamente:

Series → Markets → Events → Outcomes

Definiciones obligatorias:

Series: contenedor lógico / agrupador.

Agrupa múltiples markets relacionados (ej. “Bitcoin Up or Down”).

NO es tradeable.

NO tiene orderbook.

NO se resuelve.

Solo se usa para descubrimiento y UX.

Market: plantilla concreta dentro de una series.

Ej.: “BTC Up or Down – 15 min”.

Define reglas, frecuencia y estructura.

NO se tradea directamente.

Event: instancia concreta y temporal de un market.

Ej.: “BTC Up or Down 18:00–18:15”.

ES lo que realmente se tradea.

Outcome: resultado dentro de un event (YES/NO, UP/DOWN).

Reglas de diseño (NO negociables):

Series nunca se activan para trading.

Solo los Markets pueden activarse/desactivarse por el usuario.

Los Events se descubren automáticamente a partir de Markets activos.

Strategy, Risk y Execution solo operan Events, nunca Series ni Markets abstractos.

Frontend:

Mostrar Series solo como capa de navegación/agrupación (opcional).

Dentro de una Series, listar Markets.

Permitir activar/desactivar Markets, no Series.

Mostrar Events como vista informativa (read-only).

Backend:

El scanner puede usar Series para descubrir Markets.

El scanner solo procesa Markets activados para descubrir Events.

EventEngine, Strategy y Execution ignoran completamente las Series.

Persistencia mínima:

series

series_id

name

markets

market_id

series_id

name

enabled

events

event_id

market_id

start_time

end_time

state

Objetivo final:

Series = organización / UX

Markets = configuración del bot

Events = operativa real

Implementar el sistema respetando esta separación estricta y evitando cualquier trading directo sobre Series o Markets abstractos. , 

En Polymarket existe una jerarquía clara y varias capas de clasificación que deben respetarse estrictamente:

Series → Markets → Events → Outcomes
       ↘
        Tags (clasificación transversal)

Definiciones obligatorias
1. Series

Contenedor lógico / agrupador de Markets relacionados.

Ej.: “Bitcoin Up or Down”.

NO es tradeable.

NO tiene orderbook.

NO se resuelve.

Se usa solo para organización y UX.

2. Market

Plantilla concreta dentro de una Series.

Ej.: “BTC Up or Down – 15 min”.

Define reglas, frecuencia y estructura.

NO se tradea directamente.

Es la unidad configurable por el usuario.

3. Event

Instancia concreta y temporal de un Market.

Ej.: “BTC Up or Down 18:00–18:15”.

ES lo que realmente se tradea.

Tiene su propio orderbook y resolución.

4. Outcome

Resultado dentro de un Event (YES/NO, UP/DOWN).

La Execution opera sobre outcomes concretos.

5. Tags

Metadatos transversales de clasificación.

Ejemplos:

crypto

bitcoin

15m

up-down

sports

Un Tag:

NO es tradeable.

NO define estructura.

NO define frecuencia.

NO tiene lógica propia.

Un Market puede tener múltiples Tags.

Reglas de diseño (NO negociables)

Series nunca se activan para trading.

Tags nunca se activan para trading.

Solo los Markets pueden activarse/desactivarse por el usuario.

Los Events se descubren automáticamente a partir de Markets activos.

Strategy, Risk y Execution solo operan Events, nunca Series, Tags ni Markets abstractos.

Uso correcto de Tags
Frontend

Los Tags se usan exclusivamente para:

búsqueda

filtrado

agrupación visual

Ejemplos:

filtrar Markets por crypto

filtrar Markets por 15m

combinar Tags (crypto + up-down)

El usuario NO activa Tags.

Backend

El scanner puede:

usar Tags para descubrir Markets

filtrar Markets antes de mostrarlos

Tags NO participan en:

Strategy

Risk

Execution

EventEngine

Persistencia mínima requerida

series

series_id

name

markets

market_id

series_id

name

enabled

tags

tag_id

name

market_tags

market_id

tag_id

events

event_id

market_id

start_time

end_time

state

Objetivo final

Series → organización de alto nivel (UX)

Tags → clasificación transversal (filtros)

Markets → configuración del bot

Events → operativa real

Implementar el sistema respetando esta separación estricta y evitando cualquier trading directo sobre Series, Tags o Markets abstractos.



APIS A FIN DE TENER TODA LA INFORMACION PERFECTA EN EL DASHBOARD DEL USUARIO: 

curl --request GET \
  --url https://gamma-api.polymarket.com/teams

200
[
  {
    "id": 123,
    "name": "<string>",
    "league": "<string>",
    "record": "<string>",
    "logo": "<string>",
    "abbreviation": "<string>",
    "alias": "<string>",
    "createdAt": "2023-11-07T05:31:56Z",
    "updatedAt": "2023-11-07T05:31:56Z"
  }
]


curl --request GET \
  --url https://gamma-api.polymarket.com/sports

200
[
  {
    "sport": "<string>",
    "image": "<string>",
    "resolution": "<string>",
    "ordering": "<string>",
    "tags": "<string>",
    "series": "<string>"
  }
]

curl --request GET \
  --url https://gamma-api.polymarket.com/tags

200
[
  {
    "id": "<string>",
    "label": "<string>",
    "slug": "<string>",
    "forceShow": true,
    "publishedAt": "<string>",
    "createdBy": 123,
    "updatedBy": 123,
    "createdAt": "2023-11-07T05:31:56Z",
    "updatedAt": "2023-11-07T05:31:56Z",
    "forceHide": true,
    "isCarousel": true
  }
]



List tags
GET
/
tags

Try it
Query Parameters
​
limit
integer
Required range: x >= 0
​
offset
integer
Required range: x >= 0
​
order
string
Comma-separated list of fields to order by

​
ascending
boolean
​
include_template
boolean
​
is_carousel
boolean
Response
200 - application/json
List of tags

​
id
string
​
label
string | null
​
slug
string | null
​
forceShow
boolean | null
​
publishedAt
string | null
​
createdBy
integer | null
​
updatedBy
integer | null
​
createdAt
string<date-time> | null
​
updatedAt
string<date-time> | null
​
forceHide
boolean | null
​
isCarousel
boolean | null

curl --request GET \
  --url https://gamma-api.polymarket.com/tags/{id}

200

404
{
  "id": "<string>",
  "label": "<string>",
  "slug": "<string>",
  "forceShow": true,
  "publishedAt": "<string>",
  "createdBy": 123,
  "updatedBy": 123,
  "createdAt": "2023-11-07T05:31:56Z",
  "updatedAt": "2023-11-07T05:31:56Z",
  "forceHide": true,
  "isCarousel": true
}


curl --request GET \
  --url https://gamma-api.polymarket.com/tags/slug/{slug}

200

404
{
  "id": "<string>",
  "label": "<string>",
  "slug": "<string>",
  "forceShow": true,
  "publishedAt": "<string>",
  "createdBy": 123,
  "updatedBy": 123,
  "createdAt": "2023-11-07T05:31:56Z",
  "updatedAt": "2023-11-07T05:31:56Z",
  "forceHide": true,
  "isCarousel": true
}

curl --request GET \
  --url https://gamma-api.polymarket.com/tags/{id}/related-tags

200
[
  {
    "id": "<string>",
    "tagID": 123,
    "relatedTagID": 123,
    "rank": 123
  }
]

curl --request GET \
  --url https://gamma-api.polymarket.com/tags/slug/{slug}/related-tags

200
[
  {
    "id": "<string>",
    "tagID": 123,
    "relatedTagID": 123,
    "rank": 123
  }
]

curl --request GET \
  --url https://gamma-api.polymarket.com/tags/{id}/related-tags/tags

200
[
  {
    "id": "<string>",
    "label": "<string>",
    "slug": "<string>",
    "forceShow": true,
    "publishedAt": "<string>",
    "createdBy": 123,
    "updatedBy": 123,
    "createdAt": "2023-11-07T05:31:56Z",
    "updatedAt": "2023-11-07T05:31:56Z",
    "forceHide": true,
    "isCarousel": true
  }
]

curl --request GET \
  --url https://gamma-api.polymarket.com/tags/slug/{slug}/related-tags/tags

200
[
  {
    "id": "<string>",
    "label": "<string>",
    "slug": "<string>",
    "forceShow": true,
    "publishedAt": "<string>",
    "createdBy": 123,
    "updatedBy": 123,
    "createdAt": "2023-11-07T05:31:56Z",
    "updatedAt": "2023-11-07T05:31:56Z",
    "forceHide": true,
    "isCarousel": true
  }
]

curl --request GET \
  --url https://gamma-api.polymarket.com/events

200
[
  {
    "id": "<string>",
    "ticker": "<string>",
    "slug": "<string>",
    "title": "<string>",
    "subtitle": "<string>",
    "description": "<string>",
    "resolutionSource": "<string>",
    "startDate": "2023-11-07T05:31:56Z",
    "creationDate": "2023-11-07T05:31:56Z",
    "endDate": "2023-11-07T05:31:56Z",
    "image": "<string>",
    "icon": "<string>",
    "active": true,
    "closed": true,
    "archived": true,
    "new": true,
    "featured": true,
    "restricted": true,
    "liquidity": 123,
    "volume": 123,
    "openInterest": 123,
    "sortBy": "<string>",
    "category": "<string>",
    "subcategory": "<string>",
    "isTemplate": true,
    "templateVariables": "<string>",
    "published_at": "<string>",
    "createdBy": "<string>",
    "updatedBy": "<string>",
    "createdAt": "2023-11-07T05:31:56Z",
    "updatedAt": "2023-11-07T05:31:56Z",
    "commentsEnabled": true,
    "competitive": 123,
    "volume24hr": 123,
    "volume1wk": 123,
    "volume1mo": 123,
    "volume1yr": 123,
    "featuredImage": "<string>",
    "disqusThread": "<string>",
    "parentEvent": "<string>",
    "enableOrderBook": true,
    "liquidityAmm": 123,
    "liquidityClob": 123,
    "negRisk": true,
    "negRiskMarketID": "<string>",
    "negRiskFeeBips": 123,
    "commentCount": 123,
    "imageOptimized": {
      "id": "<string>",
      "imageUrlSource": "<string>",
      "imageUrlOptimized": "<string>",
      "imageSizeKbSource": 123,
      "imageSizeKbOptimized": 123,
      "imageOptimizedComplete": true,
      "imageOptimizedLastUpdated": "<string>",
      "relID": 123,
      "field": "<string>",
      "relname": "<string>"
    },
    "iconOptimized": {
      "id": "<string>",
      "imageUrlSource": "<string>",
      "imageUrlOptimized": "<string>",
      "imageSizeKbSource": 123,
      "imageSizeKbOptimized": 123,
      "imageOptimizedComplete": true,
      "imageOptimizedLastUpdated": "<string>",
      "relID": 123,
      "field": "<string>",
      "relname": "<string>"
    },
    "featuredImageOptimized": {
      "id": "<string>",
      "imageUrlSource": "<string>",
      "imageUrlOptimized": "<string>",
      "imageSizeKbSource": 123,
      "imageSizeKbOptimized": 123,
      "imageOptimizedComplete": true,
      "imageOptimizedLastUpdated": "<string>",
      "relID": 123,
      "field": "<string>",
      "relname": "<string>"
    },
    "subEvents": [
      "<string>"
    ],
    "markets": [
      {
        "id": "<string>",
        "question": "<string>",
        "conditionId": "<string>",
        "slug": "<string>",
        "twitterCardImage": "<string>",
        "resolutionSource": "<string>",
        "endDate": "2023-11-07T05:31:56Z",
        "category": "<string>",
        "ammType": "<string>",
        "liquidity": "<string>",
        "sponsorName": "<string>",
        "sponsorImage": "<string>",
        "startDate": "2023-11-07T05:31:56Z",
        "xAxisValue": "<string>",
        "yAxisValue": "<string>",
        "denominationToken": "<string>",
        "fee": "<string>",
        "image": "<string>",
        "icon": "<string>",
        "lowerBound": "<string>",
        "upperBound": "<string>",
        "description": "<string>",
        "outcomes": "<string>",
        "outcomePrices": "<string>",
        "volume": "<string>",
        "active": true,
        "marketType": "<string>",
        "formatType": "<string>",
        "lowerBoundDate": "<string>",
        "upperBoundDate": "<string>",
        "closed": true,
        "marketMakerAddress": "<string>",
        "createdBy": 123,
        "updatedBy": 123,
        "createdAt": "2023-11-07T05:31:56Z",
        "updatedAt": "2023-11-07T05:31:56Z",
        "closedTime": "<string>",
        "wideFormat": true,
        "new": true,
        "mailchimpTag": "<string>",
        "featured": true,
        "archived": true,
        "resolvedBy": "<string>",
        "restricted": true,
        "marketGroup": 123,
        "groupItemTitle": "<string>",
        "groupItemThreshold": "<string>",
        "questionID": "<string>",
        "umaEndDate": "<string>",
        "enableOrderBook": true,
        "orderPriceMinTickSize": 123,
        "orderMinSize": 123,
        "umaResolutionStatus": "<string>",
        "curationOrder": 123,
        "volumeNum": 123,
        "liquidityNum": 123,
        "endDateIso": "<string>",
        "startDateIso": "<string>",
        "umaEndDateIso": "<string>",
        "hasReviewedDates": true,
        "readyForCron": true,
        "commentsEnabled": true,
        "volume24hr": 123,
        "volume1wk": 123,
        "volume1mo": 123,
        "volume1yr": 123,
        "gameStartTime": "<string>",
        "secondsDelay": 123,
        "clobTokenIds": "<string>",
        "disqusThread": "<string>",
        "shortOutcomes": "<string>",
        "teamAID": "<string>",
        "teamBID": "<string>",
        "umaBond": "<string>",
        "umaReward": "<string>",
        "fpmmLive": true,
        "volume24hrAmm": 123,
        "volume1wkAmm": 123,
        "volume1moAmm": 123,
        "volume1yrAmm": 123,
        "volume24hrClob": 123,
        "volume1wkClob": 123,
        "volume1moClob": 123,
        "volume1yrClob": 123,
        "volumeAmm": 123,
        "volumeClob": 123,
        "liquidityAmm": 123,
        "liquidityClob": 123,
        "makerBaseFee": 123,
        "takerBaseFee": 123,
        "customLiveness": 123,
        "acceptingOrders": true,
        "notificationsEnabled": true,
        "score": 123,
        "imageOptimized": {
          "id": "<string>",
          "imageUrlSource": "<string>",
          "imageUrlOptimized": "<string>",
          "imageSizeKbSource": 123,
          "imageSizeKbOptimized": 123,
          "imageOptimizedComplete": true,
          "imageOptimizedLastUpdated": "<string>",
          "relID": 123,
          "field": "<string>",
          "relname": "<string>"
        },
        "iconOptimized": {
          "id": "<string>",
          "imageUrlSource": "<string>",
          "imageUrlOptimized": "<string>",
          "imageSizeKbSource": 123,
          "imageSizeKbOptimized": 123,
          "imageOptimizedComplete": true,
          "imageOptimizedLastUpdated": "<string>",
          "relID": 123,
          "field": "<string>",
          "relname": "<string>"
        },
        "events": "<array>",
        "categories": [
          {
            "id": "<string>",
            "label": "<string>",
            "parentCategory": "<string>",
            "slug": "<string>",
            "publishedAt": "<string>",
            "createdBy": "<string>",
            "updatedBy": "<string>",
            "createdAt": "2023-11-07T05:31:56Z",
            "updatedAt": "2023-11-07T05:31:56Z"
          }
        ],
        "tags": [
          {
            "id": "<string>",
            "label": "<string>",
            "slug": "<string>",
            "forceShow": true,
            "publishedAt": "<string>",
            "createdBy": 123,
            "updatedBy": 123,
            "createdAt": "2023-11-07T05:31:56Z",
            "updatedAt": "2023-11-07T05:31:56Z",
            "forceHide": true,
            "isCarousel": true
          }
        ],
        "creator": "<string>",
        "ready": true,
        "funded": true,
        "pastSlugs": "<string>",
        "readyTimestamp": "2023-11-07T05:31:56Z",
        "fundedTimestamp": "2023-11-07T05:31:56Z",
        "acceptingOrdersTimestamp": "2023-11-07T05:31:56Z",
        "competitive": 123,
        "rewardsMinSize": 123,
        "rewardsMaxSpread": 123,
        "spread": 123,
        "automaticallyResolved": true,
        "oneDayPriceChange": 123,
        "oneHourPriceChange": 123,
        "oneWeekPriceChange": 123,
        "oneMonthPriceChange": 123,
        "oneYearPriceChange": 123,
        "lastTradePrice": 123,
        "bestBid": 123,
        "bestAsk": 123,
        "automaticallyActive": true,
        "clearBookOnStart": true,
        "chartColor": "<string>",
        "seriesColor": "<string>",
        "showGmpSeries": true,
        "showGmpOutcome": true,
        "manualActivation": true,
        "negRiskOther": true,
        "gameId": "<string>",
        "groupItemRange": "<string>",
        "sportsMarketType": "<string>",
        "line": 123,
        "umaResolutionStatuses": "<string>",
        "pendingDeployment": true,
        "deploying": true,
        "deployingTimestamp": "2023-11-07T05:31:56Z",
        "scheduledDeploymentTimestamp": "2023-11-07T05:31:56Z",
        "rfqEnabled": true,
        "eventStartTime": "2023-11-07T05:31:56Z"
      }
    ],
    "series": [
      {
        "id": "<string>",
        "ticker": "<string>",
        "slug": "<string>",
        "title": "<string>",
        "subtitle": "<string>",
        "seriesType": "<string>",
        "recurrence": "<string>",
        "description": "<string>",
        "image": "<string>",
        "icon": "<string>",
        "layout": "<string>",
        "active": true,
        "closed": true,
        "archived": true,
        "new": true,
        "featured": true,
        "restricted": true,
        "isTemplate": true,
        "templateVariables": true,
        "publishedAt": "<string>",
        "createdBy": "<string>",
        "updatedBy": "<string>",
        "createdAt": "2023-11-07T05:31:56Z",
        "updatedAt": "2023-11-07T05:31:56Z",
        "commentsEnabled": true,
        "competitive": "<string>",
        "volume24hr": 123,
        "volume": 123,
        "liquidity": 123,
        "startDate": "2023-11-07T05:31:56Z",
        "pythTokenID": "<string>",
        "cgAssetName": "<string>",
        "score": 123,
        "events": "<array>",
        "collections": [
          {
            "id": "<string>",
            "ticker": "<string>",
            "slug": "<string>",
            "title": "<string>",
            "subtitle": "<string>",
            "collectionType": "<string>",
            "description": "<string>",
            "tags": "<string>",
            "image": "<string>",
            "icon": "<string>",
            "headerImage": "<string>",
            "layout": "<string>",
            "active": true,
            "closed": true,
            "archived": true,
            "new": true,
            "featured": true,
            "restricted": true,
            "isTemplate": true,
            "templateVariables": "<string>",
            "publishedAt": "<string>",
            "createdBy": "<string>",
            "updatedBy": "<string>",
            "createdAt": "2023-11-07T05:31:56Z",
            "updatedAt": "2023-11-07T05:31:56Z",
            "commentsEnabled": true,
            "imageOptimized": {
              "id": "<string>",
              "imageUrlSource": "<string>",
              "imageUrlOptimized": "<string>",
              "imageSizeKbSource": 123,
              "imageSizeKbOptimized": 123,
              "imageOptimizedComplete": true,
              "imageOptimizedLastUpdated": "<string>",
              "relID": 123,
              "field": "<string>",
              "relname": "<string>"
            },
            "iconOptimized": {
              "id": "<string>",
              "imageUrlSource": "<string>",
              "imageUrlOptimized": "<string>",
              "imageSizeKbSource": 123,
              "imageSizeKbOptimized": 123,
              "imageOptimizedComplete": true,
              "imageOptimizedLastUpdated": "<string>",
              "relID": 123,
              "field": "<string>",
              "relname": "<string>"
            },
            "headerImageOptimized": {
              "id": "<string>",
              "imageUrlSource": "<string>",
              "imageUrlOptimized": "<string>",
              "imageSizeKbSource": 123,
              "imageSizeKbOptimized": 123,
              "imageOptimizedComplete": true,
              "imageOptimizedLastUpdated": "<string>",
              "relID": 123,
              "field": "<string>",
              "relname": "<string>"
            }
          }
        ],
        "categories": [
          {
            "id": "<string>",
            "label": "<string>",
            "parentCategory": "<string>",
            "slug": "<string>",
            "publishedAt": "<string>",
            "createdBy": "<string>",
            "updatedBy": "<string>",
            "createdAt": "2023-11-07T05:31:56Z",
            "updatedAt": "2023-11-07T05:31:56Z"
          }
        ],
        "tags": [
          {
            "id": "<string>",
            "label": "<string>",
            "slug": "<string>",
            "forceShow": true,
            "publishedAt": "<string>",
            "createdBy": 123,
            "updatedBy": 123,
            "createdAt": "2023-11-07T05:31:56Z",
            "updatedAt": "2023-11-07T05:31:56Z",
            "forceHide": true,
            "isCarousel": true
          }
        ],
        "commentCount": 123,
        "chats": [
          {
            "id": "<string>",
            "channelId": "<string>",
            "channelName": "<string>",
            "channelImage": "<string>",
            "live": true,
            "startTime": "2023-11-07T05:31:56Z",
            "endTime": "2023-11-07T05:31:56Z"
          }
        ]
      }
    ],
    "categories": [
      {
        "id": "<string>",
        "label": "<string>",
        "parentCategory": "<string>",
        "slug": "<string>",
        "publishedAt": "<string>",
        "createdBy": "<string>",
        "updatedBy": "<string>",
        "createdAt": "2023-11-07T05:31:56Z",
        "updatedAt": "2023-11-07T05:31:56Z"
      }
    ],
    "collections": [
      {
        "id": "<string>",
        "ticker": "<string>",
        "slug": "<string>",
        "title": "<string>",
        "subtitle": "<string>",
        "collectionType": "<string>",
        "description": "<string>",
        "tags": "<string>",
        "image": "<string>",
        "icon": "<string>",
        "headerImage": "<string>",
        "layout": "<string>",
        "active": true,
        "closed": true,
        "archived": true,
        "new": true,
        "featured": true,
        "restricted": true,
        "isTemplate": true,
        "templateVariables": "<string>",
        "publishedAt": "<string>",
        "createdBy": "<string>",
        "updatedBy": "<string>",
        "createdAt": "2023-11-07T05:31:56Z",
        "updatedAt": "2023-11-07T05:31:56Z",
        "commentsEnabled": true,
        "imageOptimized": {
          "id": "<string>",
          "imageUrlSource": "<string>",
          "imageUrlOptimized": "<string>",
          "imageSizeKbSource": 123,
          "imageSizeKbOptimized": 123,
          "imageOptimizedComplete": true,
          "imageOptimizedLastUpdated": "<string>",
          "relID": 123,
          "field": "<string>",
          "relname": "<string>"
        },
        "iconOptimized": {
          "id": "<string>",
          "imageUrlSource": "<string>",
          "imageUrlOptimized": "<string>",
          "imageSizeKbSource": 123,
          "imageSizeKbOptimized": 123,
          "imageOptimizedComplete": true,
          "imageOptimizedLastUpdated": "<string>",
          "relID": 123,
          "field": "<string>",
          "relname": "<string>"
        },
        "headerImageOptimized": {
          "id": "<string>",
          "imageUrlSource": "<string>",
          "imageUrlOptimized": "<string>",
          "imageSizeKbSource": 123,
          "imageSizeKbOptimized": 123,
          "imageOptimizedComplete": true,
          "imageOptimizedLastUpdated": "<string>",
          "relID": 123,
          "field": "<string>",
          "relname": "<string>"
        }
      }
    ],
    "tags": [
      {
        "id": "<string>",
        "label": "<string>",
        "slug": "<string>",
        "forceShow": true,
        "publishedAt": "<string>",
        "createdBy": 123,
        "updatedBy": 123,
        "createdAt": "2023-11-07T05:31:56Z",
        "updatedAt": "2023-11-07T05:31:56Z",
        "forceHide": true,
        "isCarousel": true
      }
    ],
    "cyom": true,
    "closedTime": "2023-11-07T05:31:56Z",
    "showAllOutcomes": true,
    "showMarketImages": true,
    "automaticallyResolved": true,
    "enableNegRisk": true,
    "automaticallyActive": true,
    "eventDate": "<string>",
    "startTime": "2023-11-07T05:31:56Z",
    "eventWeek": 123,
    "seriesSlug": "<string>",
    "score": "<string>",
    "elapsed": "<string>",
    "period": "<string>",
    "live": true,
    "ended": true,
    "finishedTimestamp": "2023-11-07T05:31:56Z",
    "gmpChartMode": "<string>",
    "eventCreators": [
      {
        "id": "<string>",
        "creatorName": "<string>",
        "creatorHandle": "<string>",
        "creatorUrl": "<string>",
        "creatorImage": "<string>",
        "createdAt": "2023-11-07T05:31:56Z",
        "updatedAt": "2023-11-07T05:31:56Z"
      }
    ],
    "tweetCount": 123,
    "chats": [
      {
        "id": "<string>",
        "channelId": "<string>",
        "channelName": "<string>",
        "channelImage": "<string>",
        "live": true,
        "startTime": "2023-11-07T05:31:56Z",
        "endTime": "2023-11-07T05:31:56Z"
      }
    ],
    "featuredOrder": 123,
    "estimateValue": true,
    "cantEstimate": true,
    "estimatedValue": "<string>",
    "templates": [
      {
        "id": "<string>",
        "eventTitle": "<string>",
        "eventSlug": "<string>",
        "eventImage": "<string>",
        "marketTitle": "<string>",
        "description": "<string>",
        "resolutionSource": "<string>",
        "negRisk": true,
        "sortBy": "<string>",
        "showMarketImages": true,
        "seriesSlug": "<string>",
        "outcomes": "<string>"
      }
    ],
    "spreadsMainLine": 123,
    "totalsMainLine": 123,
    "carouselMap": "<string>",
    "pendingDeployment": true,
    "deploying": true,
    "deployingTimestamp": "2023-11-07T05:31:56Z",
    "scheduledDeploymentTimestamp": "2023-11-07T05:31:56Z",
    "gameStatus": "<string>"
  }
]

curl --request GET \
  --url https://gamma-api.polymarket.com/events/{id}

200

404
{
  "id": "<string>",
  "ticker": "<string>",
  "slug": "<string>",
  "title": "<string>",
  "subtitle": "<string>",
  "description": "<string>",
  "resolutionSource": "<string>",
  "startDate": "2023-11-07T05:31:56Z",
  "creationDate": "2023-11-07T05:31:56Z",
  "endDate": "2023-11-07T05:31:56Z",
  "image": "<string>",
  "icon": "<string>",
  "active": true,
  "closed": true,
  "archived": true,
  "new": true,
  "featured": true,
  "restricted": true,
  "liquidity": 123,
  "volume": 123,
  "openInterest": 123,
  "sortBy": "<string>",
  "category": "<string>",
  "subcategory": "<string>",
  "isTemplate": true,
  "templateVariables": "<string>",
  "published_at": "<string>",
  "createdBy": "<string>",
  "updatedBy": "<string>",
  "createdAt": "2023-11-07T05:31:56Z",
  "updatedAt": "2023-11-07T05:31:56Z",
  "commentsEnabled": true,
  "competitive": 123,
  "volume24hr": 123,
  "volume1wk": 123,
  "volume1mo": 123,
  "volume1yr": 123,
  "featuredImage": "<string>",
  "disqusThread": "<string>",
  "parentEvent": "<string>",
  "enableOrderBook": true,
  "liquidityAmm": 123,
  "liquidityClob": 123,
  "negRisk": true,
  "negRiskMarketID": "<string>",
  "negRiskFeeBips": 123,
  "commentCount": 123,
  "imageOptimized": {
    "id": "<string>",
    "imageUrlSource": "<string>",
    "imageUrlOptimized": "<string>",
    "imageSizeKbSource": 123,
    "imageSizeKbOptimized": 123,
    "imageOptimizedComplete": true,
    "imageOptimizedLastUpdated": "<string>",
    "relID": 123,
    "field": "<string>",
    "relname": "<string>"
  },
  "iconOptimized": {
    "id": "<string>",
    "imageUrlSource": "<string>",
    "imageUrlOptimized": "<string>",
    "imageSizeKbSource": 123,
    "imageSizeKbOptimized": 123,
    "imageOptimizedComplete": true,
    "imageOptimizedLastUpdated": "<string>",
    "relID": 123,
    "field": "<string>",
    "relname": "<string>"
  },
  "featuredImageOptimized": {
    "id": "<string>",
    "imageUrlSource": "<string>",
    "imageUrlOptimized": "<string>",
    "imageSizeKbSource": 123,
    "imageSizeKbOptimized": 123,
    "imageOptimizedComplete": true,
    "imageOptimizedLastUpdated": "<string>",
    "relID": 123,
    "field": "<string>",
    "relname": "<string>"
  },
  "subEvents": [
    "<string>"
  ],
  "markets": [
    {
      "id": "<string>",
      "question": "<string>",
      "conditionId": "<string>",
      "slug": "<string>",
      "twitterCardImage": "<string>",
      "resolutionSource": "<string>",
      "endDate": "2023-11-07T05:31:56Z",
      "category": "<string>",
      "ammType": "<string>",
      "liquidity": "<string>",
      "sponsorName": "<string>",
      "sponsorImage": "<string>",
      "startDate": "2023-11-07T05:31:56Z",
      "xAxisValue": "<string>",
      "yAxisValue": "<string>",
      "denominationToken": "<string>",
      "fee": "<string>",
      "image": "<string>",
      "icon": "<string>",
      "lowerBound": "<string>",
      "upperBound": "<string>",
      "description": "<string>",
      "outcomes": "<string>",
      "outcomePrices": "<string>",
      "volume": "<string>",
      "active": true,
      "marketType": "<string>",
      "formatType": "<string>",
      "lowerBoundDate": "<string>",
      "upperBoundDate": "<string>",
      "closed": true,
      "marketMakerAddress": "<string>",
      "createdBy": 123,
      "updatedBy": 123,
      "createdAt": "2023-11-07T05:31:56Z",
      "updatedAt": "2023-11-07T05:31:56Z",
      "closedTime": "<string>",
      "wideFormat": true,
      "new": true,
      "mailchimpTag": "<string>",
      "featured": true,
      "archived": true,
      "resolvedBy": "<string>",
      "restricted": true,
      "marketGroup": 123,
      "groupItemTitle": "<string>",
      "groupItemThreshold": "<string>",
      "questionID": "<string>",
      "umaEndDate": "<string>",
      "enableOrderBook": true,
      "orderPriceMinTickSize": 123,
      "orderMinSize": 123,
      "umaResolutionStatus": "<string>",
      "curationOrder": 123,
      "volumeNum": 123,
      "liquidityNum": 123,
      "endDateIso": "<string>",
      "startDateIso": "<string>",
      "umaEndDateIso": "<string>",
      "hasReviewedDates": true,
      "readyForCron": true,
      "commentsEnabled": true,
      "volume24hr": 123,
      "volume1wk": 123,
      "volume1mo": 123,
      "volume1yr": 123,
      "gameStartTime": "<string>",
      "secondsDelay": 123,
      "clobTokenIds": "<string>",
      "disqusThread": "<string>",
      "shortOutcomes": "<string>",
      "teamAID": "<string>",
      "teamBID": "<string>",
      "umaBond": "<string>",
      "umaReward": "<string>",
      "fpmmLive": true,
      "volume24hrAmm": 123,
      "volume1wkAmm": 123,
      "volume1moAmm": 123,
      "volume1yrAmm": 123,
      "volume24hrClob": 123,
      "volume1wkClob": 123,
      "volume1moClob": 123,
      "volume1yrClob": 123,
      "volumeAmm": 123,
      "volumeClob": 123,
      "liquidityAmm": 123,
      "liquidityClob": 123,
      "makerBaseFee": 123,
      "takerBaseFee": 123,
      "customLiveness": 123,
      "acceptingOrders": true,
      "notificationsEnabled": true,
      "score": 123,
      "imageOptimized": {
        "id": "<string>",
        "imageUrlSource": "<string>",
        "imageUrlOptimized": "<string>",
        "imageSizeKbSource": 123,
        "imageSizeKbOptimized": 123,
        "imageOptimizedComplete": true,
        "imageOptimizedLastUpdated": "<string>",
        "relID": 123,
        "field": "<string>",
        "relname": "<string>"
      },
      "iconOptimized": {
        "id": "<string>",
        "imageUrlSource": "<string>",
        "imageUrlOptimized": "<string>",
        "imageSizeKbSource": 123,
        "imageSizeKbOptimized": 123,
        "imageOptimizedComplete": true,
        "imageOptimizedLastUpdated": "<string>",
        "relID": 123,
        "field": "<string>",
        "relname": "<string>"
      },
      "events": "<array>",
      "categories": [
        {
          "id": "<string>",
          "label": "<string>",
          "parentCategory": "<string>",
          "slug": "<string>",
          "publishedAt": "<string>",
          "createdBy": "<string>",
          "updatedBy": "<string>",
          "createdAt": "2023-11-07T05:31:56Z",
          "updatedAt": "2023-11-07T05:31:56Z"
        }
      ],
      "tags": [
        {
          "id": "<string>",
          "label": "<string>",
          "slug": "<string>",
          "forceShow": true,
          "publishedAt": "<string>",
          "createdBy": 123,
          "updatedBy": 123,
          "createdAt": "2023-11-07T05:31:56Z",
          "updatedAt": "2023-11-07T05:31:56Z",
          "forceHide": true,
          "isCarousel": true
        }
      ],
      "creator": "<string>",
      "ready": true,
      "funded": true,
      "pastSlugs": "<string>",
      "readyTimestamp": "2023-11-07T05:31:56Z",
      "fundedTimestamp": "2023-11-07T05:31:56Z",
      "acceptingOrdersTimestamp": "2023-11-07T05:31:56Z",
      "competitive": 123,
      "rewardsMinSize": 123,
      "rewardsMaxSpread": 123,
      "spread": 123,
      "automaticallyResolved": true,
      "oneDayPriceChange": 123,
      "oneHourPriceChange": 123,
      "oneWeekPriceChange": 123,
      "oneMonthPriceChange": 123,
      "oneYearPriceChange": 123,
      "lastTradePrice": 123,
      "bestBid": 123,
      "bestAsk": 123,
      "automaticallyActive": true,
      "clearBookOnStart": true,
      "chartColor": "<string>",
      "seriesColor": "<string>",
      "showGmpSeries": true,
      "showGmpOutcome": true,
      "manualActivation": true,
      "negRiskOther": true,
      "gameId": "<string>",
      "groupItemRange": "<string>",
      "sportsMarketType": "<string>",
      "line": 123,
      "umaResolutionStatuses": "<string>",
      "pendingDeployment": true,
      "deploying": true,
      "deployingTimestamp": "2023-11-07T05:31:56Z",
      "scheduledDeploymentTimestamp": "2023-11-07T05:31:56Z",
      "rfqEnabled": true,
      "eventStartTime": "2023-11-07T05:31:56Z"
    }
  ],
  "series": [
    {
      "id": "<string>",
      "ticker": "<string>",
      "slug": "<string>",
      "title": "<string>",
      "subtitle": "<string>",
      "seriesType": "<string>",
      "recurrence": "<string>",
      "description": "<string>",
      "image": "<string>",
      "icon": "<string>",
      "layout": "<string>",
      "active": true,
      "closed": true,
      "archived": true,
      "new": true,
      "featured": true,
      "restricted": true,
      "isTemplate": true,
      "templateVariables": true,
      "publishedAt": "<string>",
      "createdBy": "<string>",
      "updatedBy": "<string>",
      "createdAt": "2023-11-07T05:31:56Z",
      "updatedAt": "2023-11-07T05:31:56Z",
      "commentsEnabled": true,
      "competitive": "<string>",
      "volume24hr": 123,
      "volume": 123,
      "liquidity": 123,
      "startDate": "2023-11-07T05:31:56Z",
      "pythTokenID": "<string>",
      "cgAssetName": "<string>",
      "score": 123,
      "events": "<array>",
      "collections": [
        {
          "id": "<string>",
          "ticker": "<string>",
          "slug": "<string>",
          "title": "<string>",
          "subtitle": "<string>",
          "collectionType": "<string>",
          "description": "<string>",
          "tags": "<string>",
          "image": "<string>",
          "icon": "<string>",
          "headerImage": "<string>",
          "layout": "<string>",
          "active": true,
          "closed": true,
          "archived": true,
          "new": true,
          "featured": true,
          "restricted": true,
          "isTemplate": true,
          "templateVariables": "<string>",
          "publishedAt": "<string>",
          "createdBy": "<string>",
          "updatedBy": "<string>",
          "createdAt": "2023-11-07T05:31:56Z",
          "updatedAt": "2023-11-07T05:31:56Z",
          "commentsEnabled": true,
          "imageOptimized": {
            "id": "<string>",
            "imageUrlSource": "<string>",
            "imageUrlOptimized": "<string>",
            "imageSizeKbSource": 123,
            "imageSizeKbOptimized": 123,
            "imageOptimizedComplete": true,
            "imageOptimizedLastUpdated": "<string>",
            "relID": 123,
            "field": "<string>",
            "relname": "<string>"
          },
          "iconOptimized": {
            "id": "<string>",
            "imageUrlSource": "<string>",
            "imageUrlOptimized": "<string>",
            "imageSizeKbSource": 123,
            "imageSizeKbOptimized": 123,
            "imageOptimizedComplete": true,
            "imageOptimizedLastUpdated": "<string>",
            "relID": 123,
            "field": "<string>",
            "relname": "<string>"
          },
          "headerImageOptimized": {
            "id": "<string>",
            "imageUrlSource": "<string>",
            "imageUrlOptimized": "<string>",
            "imageSizeKbSource": 123,
            "imageSizeKbOptimized": 123,
            "imageOptimizedComplete": true,
            "imageOptimizedLastUpdated": "<string>",
            "relID": 123,
            "field": "<string>",
            "relname": "<string>"
          }
        }
      ],
      "categories": [
        {
          "id": "<string>",
          "label": "<string>",
          "parentCategory": "<string>",
          "slug": "<string>",
          "publishedAt": "<string>",
          "createdBy": "<string>",
          "updatedBy": "<string>",
          "createdAt": "2023-11-07T05:31:56Z",
          "updatedAt": "2023-11-07T05:31:56Z"
        }
      ],
      "tags": [
        {
          "id": "<string>",
          "label": "<string>",
          "slug": "<string>",
          "forceShow": true,
          "publishedAt": "<string>",
          "createdBy": 123,
          "updatedBy": 123,
          "createdAt": "2023-11-07T05:31:56Z",
          "updatedAt": "2023-11-07T05:31:56Z",
          "forceHide": true,
          "isCarousel": true
        }
      ],
      "commentCount": 123,
      "chats": [
        {
          "id": "<string>",
          "channelId": "<string>",
          "channelName": "<string>",
          "channelImage": "<string>",
          "live": true,
          "startTime": "2023-11-07T05:31:56Z",
          "endTime": "2023-11-07T05:31:56Z"
        }
      ]
    }
  ],
  "categories": [
    {
      "id": "<string>",
      "label": "<string>",
      "parentCategory": "<string>",
      "slug": "<string>",
      "publishedAt": "<string>",
      "createdBy": "<string>",
      "updatedBy": "<string>",
      "createdAt": "2023-11-07T05:31:56Z",
      "updatedAt": "2023-11-07T05:31:56Z"
    }
  ],
  "collections": [
    {
      "id": "<string>",
      "ticker": "<string>",
      "slug": "<string>",
      "title": "<string>",
      "subtitle": "<string>",
      "collectionType": "<string>",
      "description": "<string>",
      "tags": "<string>",
      "image": "<string>",
      "icon": "<string>",
      "headerImage": "<string>",
      "layout": "<string>",
      "active": true,
      "closed": true,
      "archived": true,
      "new": true,
      "featured": true,
      "restricted": true,
      "isTemplate": true,
      "templateVariables": "<string>",
      "publishedAt": "<string>",
      "createdBy": "<string>",
      "updatedBy": "<string>",
      "createdAt": "2023-11-07T05:31:56Z",
      "updatedAt": "2023-11-07T05:31:56Z",
      "commentsEnabled": true,
      "imageOptimized": {
        "id": "<string>",
        "imageUrlSource": "<string>",
        "imageUrlOptimized": "<string>",
        "imageSizeKbSource": 123,
        "imageSizeKbOptimized": 123,
        "imageOptimizedComplete": true,
        "imageOptimizedLastUpdated": "<string>",
        "relID": 123,
        "field": "<string>",
        "relname": "<string>"
      },
      "iconOptimized": {
        "id": "<string>",
        "imageUrlSource": "<string>",
        "imageUrlOptimized": "<string>",
        "imageSizeKbSource": 123,
        "imageSizeKbOptimized": 123,
        "imageOptimizedComplete": true,
        "imageOptimizedLastUpdated": "<string>",
        "relID": 123,
        "field": "<string>",
        "relname": "<string>"
      },
      "headerImageOptimized": {
        "id": "<string>",
        "imageUrlSource": "<string>",
        "imageUrlOptimized": "<string>",
        "imageSizeKbSource": 123,
        "imageSizeKbOptimized": 123,
        "imageOptimizedComplete": true,
        "imageOptimizedLastUpdated": "<string>",
        "relID": 123,
        "field": "<string>",
        "relname": "<string>"
      }
    }
  ],
  "tags": [
    {
      "id": "<string>",
      "label": "<string>",
      "slug": "<string>",
      "forceShow": true,
      "publishedAt": "<string>",
      "createdBy": 123,
      "updatedBy": 123,
      "createdAt": "2023-11-07T05:31:56Z",
      "updatedAt": "2023-11-07T05:31:56Z",
      "forceHide": true,
      "isCarousel": true
    }
  ],
  "cyom": true,
  "closedTime": "2023-11-07T05:31:56Z",
  "showAllOutcomes": true,
  "showMarketImages": true,
  "automaticallyResolved": true,
  "enableNegRisk": true,
  "automaticallyActive": true,
  "eventDate": "<string>",
  "startTime": "2023-11-07T05:31:56Z",
  "eventWeek": 123,
  "seriesSlug": "<string>",
  "score": "<string>",
  "elapsed": "<string>",
  "period": "<string>",
  "live": true,
  "ended": true,
  "finishedTimestamp": "2023-11-07T05:31:56Z",
  "gmpChartMode": "<string>",
  "eventCreators": [
    {
      "id": "<string>",
      "creatorName": "<string>",
      "creatorHandle": "<string>",
      "creatorUrl": "<string>",
      "creatorImage": "<string>",
      "createdAt": "2023-11-07T05:31:56Z",
      "updatedAt": "2023-11-07T05:31:56Z"
    }
  ],
  "tweetCount": 123,
  "chats": [
    {
      "id": "<string>",
      "channelId": "<string>",
      "channelName": "<string>",
      "channelImage": "<string>",
      "live": true,
      "startTime": "2023-11-07T05:31:56Z",
      "endTime": "2023-11-07T05:31:56Z"
    }
  ],
  "featuredOrder": 123,
  "estimateValue": true,
  "cantEstimate": true,
  "estimatedValue": "<string>",
  "templates": [
    {
      "id": "<string>",
      "eventTitle": "<string>",
      "eventSlug": "<string>",
      "eventImage": "<string>",
      "marketTitle": "<string>",
      "description": "<string>",
      "resolutionSource": "<string>",
      "negRisk": true,
      "sortBy": "<string>",
      "showMarketImages": true,
      "seriesSlug": "<string>",
      "outcomes": "<string>"
    }
  ],
  "spreadsMainLine": 123,
  "totalsMainLine": 123,
  "carouselMap": "<string>",
  "pendingDeployment": true,
  "deploying": true,
  "deployingTimestamp": "2023-11-07T05:31:56Z",
  "scheduledDeploymentTimestamp": "2023-11-07T05:31:56Z",
  "gameStatus": "<string>"
}

curl --request GET \
  --url https://gamma-api.polymarket.com/events/{id}/tags

200

404
[
  {
    "id": "<string>",
    "label": "<string>",
    "slug": "<string>",
    "forceShow": true,
    "publishedAt": "<string>",
    "createdBy": 123,
    "updatedBy": 123,
    "createdAt": "2023-11-07T05:31:56Z",
    "updatedAt": "2023-11-07T05:31:56Z",
    "forceHide": true,
    "isCarousel": true
  }
]

Get event by slug

curl --request GET \
  --url https://gamma-api.polymarket.com/events/slug/{slug}

200

404
{
  "id": "<string>",
  "ticker": "<string>",
  "slug": "<string>",
  "title": "<string>",
  "subtitle": "<string>",
  "description": "<string>",
  "resolutionSource": "<string>",
  "startDate": "2023-11-07T05:31:56Z",
  "creationDate": "2023-11-07T05:31:56Z",
  "endDate": "2023-11-07T05:31:56Z",
  "image": "<string>",
  "icon": "<string>",
  "active": true,
  "closed": true,
  "archived": true,
  "new": true,
  "featured": true,
  "restricted": true,
  "liquidity": 123,
  "volume": 123,
  "openInterest": 123,
  "sortBy": "<string>",
  "category": "<string>",
  "subcategory": "<string>",
  "isTemplate": true,
  "templateVariables": "<string>",
  "published_at": "<string>",
  "createdBy": "<string>",
  "updatedBy": "<string>",
  "createdAt": "2023-11-07T05:31:56Z",
  "updatedAt": "2023-11-07T05:31:56Z",
  "commentsEnabled": true,
  "competitive": 123,
  "volume24hr": 123,
  "volume1wk": 123,
  "volume1mo": 123,
  "volume1yr": 123,
  "featuredImage": "<string>",
  "disqusThread": "<string>",
  "parentEvent": "<string>",
  "enableOrderBook": true,
  "liquidityAmm": 123,
  "liquidityClob": 123,
  "negRisk": true,
  "negRiskMarketID": "<string>",
  "negRiskFeeBips": 123,
  "commentCount": 123,
  "imageOptimized": {
    "id": "<string>",
    "imageUrlSource": "<string>",
    "imageUrlOptimized": "<string>",
    "imageSizeKbSource": 123,
    "imageSizeKbOptimized": 123,
    "imageOptimizedComplete": true,
    "imageOptimizedLastUpdated": "<string>",
    "relID": 123,
    "field": "<string>",
    "relname": "<string>"
  },
  "iconOptimized": {
    "id": "<string>",
    "imageUrlSource": "<string>",
    "imageUrlOptimized": "<string>",
    "imageSizeKbSource": 123,
    "imageSizeKbOptimized": 123,
    "imageOptimizedComplete": true,
    "imageOptimizedLastUpdated": "<string>",
    "relID": 123,
    "field": "<string>",
    "relname": "<string>"
  },
  "featuredImageOptimized": {
    "id": "<string>",
    "imageUrlSource": "<string>",
    "imageUrlOptimized": "<string>",
    "imageSizeKbSource": 123,
    "imageSizeKbOptimized": 123,
    "imageOptimizedComplete": true,
    "imageOptimizedLastUpdated": "<string>",
    "relID": 123,
    "field": "<string>",
    "relname": "<string>"
  },
  "subEvents": [
    "<string>"
  ],
  "markets": [
    {
      "id": "<string>",
      "question": "<string>",
      "conditionId": "<string>",
      "slug": "<string>",
      "twitterCardImage": "<string>",
      "resolutionSource": "<string>",
      "endDate": "2023-11-07T05:31:56Z",
      "category": "<string>",
      "ammType": "<string>",
      "liquidity": "<string>",
      "sponsorName": "<string>",
      "sponsorImage": "<string>",
      "startDate": "2023-11-07T05:31:56Z",
      "xAxisValue": "<string>",
      "yAxisValue": "<string>",
      "denominationToken": "<string>",
      "fee": "<string>",
      "image": "<string>",
      "icon": "<string>",
      "lowerBound": "<string>",
      "upperBound": "<string>",
      "description": "<string>",
      "outcomes": "<string>",
      "outcomePrices": "<string>",
      "volume": "<string>",
      "active": true,
      "marketType": "<string>",
      "formatType": "<string>",
      "lowerBoundDate": "<string>",
      "upperBoundDate": "<string>",
      "closed": true,
      "marketMakerAddress": "<string>",
      "createdBy": 123,
      "updatedBy": 123,
      "createdAt": "2023-11-07T05:31:56Z",
      "updatedAt": "2023-11-07T05:31:56Z",
      "closedTime": "<string>",
      "wideFormat": true,
      "new": true,
      "mailchimpTag": "<string>",
      "featured": true,
      "archived": true,
      "resolvedBy": "<string>",
      "restricted": true,
      "marketGroup": 123,
      "groupItemTitle": "<string>",
      "groupItemThreshold": "<string>",
      "questionID": "<string>",
      "umaEndDate": "<string>",
      "enableOrderBook": true,
      "orderPriceMinTickSize": 123,
      "orderMinSize": 123,
      "umaResolutionStatus": "<string>",
      "curationOrder": 123,
      "volumeNum": 123,
      "liquidityNum": 123,
      "endDateIso": "<string>",
      "startDateIso": "<string>",
      "umaEndDateIso": "<string>",
      "hasReviewedDates": true,
      "readyForCron": true,
      "commentsEnabled": true,
      "volume24hr": 123,
      "volume1wk": 123,
      "volume1mo": 123,
      "volume1yr": 123,
      "gameStartTime": "<string>",
      "secondsDelay": 123,
      "clobTokenIds": "<string>",
      "disqusThread": "<string>",
      "shortOutcomes": "<string>",
      "teamAID": "<string>",
      "teamBID": "<string>",
      "umaBond": "<string>",
      "umaReward": "<string>",
      "fpmmLive": true,
      "volume24hrAmm": 123,
      "volume1wkAmm": 123,
      "volume1moAmm": 123,
      "volume1yrAmm": 123,
      "volume24hrClob": 123,
      "volume1wkClob": 123,
      "volume1moClob": 123,
      "volume1yrClob": 123,
      "volumeAmm": 123,
      "volumeClob": 123,
      "liquidityAmm": 123,
      "liquidityClob": 123,
      "makerBaseFee": 123,
      "takerBaseFee": 123,
      "customLiveness": 123,
      "acceptingOrders": true,
      "notificationsEnabled": true,
      "score": 123,
      "imageOptimized": {
        "id": "<string>",
        "imageUrlSource": "<string>",
        "imageUrlOptimized": "<string>",
        "imageSizeKbSource": 123,
        "imageSizeKbOptimized": 123,
        "imageOptimizedComplete": true,
        "imageOptimizedLastUpdated": "<string>",
        "relID": 123,
        "field": "<string>",
        "relname": "<string>"
      },
      "iconOptimized": {
        "id": "<string>",
        "imageUrlSource": "<string>",
        "imageUrlOptimized": "<string>",
        "imageSizeKbSource": 123,
        "imageSizeKbOptimized": 123,
        "imageOptimizedComplete": true,
        "imageOptimizedLastUpdated": "<string>",
        "relID": 123,
        "field": "<string>",
        "relname": "<string>"
      },
      "events": "<array>",
      "categories": [
        {
          "id": "<string>",
          "label": "<string>",
          "parentCategory": "<string>",
          "slug": "<string>",
          "publishedAt": "<string>",
          "createdBy": "<string>",
          "updatedBy": "<string>",
          "createdAt": "2023-11-07T05:31:56Z",
          "updatedAt": "2023-11-07T05:31:56Z"
        }
      ],
      "tags": [
        {
          "id": "<string>",
          "label": "<string>",
          "slug": "<string>",
          "forceShow": true,
          "publishedAt": "<string>",
          "createdBy": 123,
          "updatedBy": 123,
          "createdAt": "2023-11-07T05:31:56Z",
          "updatedAt": "2023-11-07T05:31:56Z",
          "forceHide": true,
          "isCarousel": true
        }
      ],
      "creator": "<string>",
      "ready": true,
      "funded": true,
      "pastSlugs": "<string>",
      "readyTimestamp": "2023-11-07T05:31:56Z",
      "fundedTimestamp": "2023-11-07T05:31:56Z",
      "acceptingOrdersTimestamp": "2023-11-07T05:31:56Z",
      "competitive": 123,
      "rewardsMinSize": 123,
      "rewardsMaxSpread": 123,
      "spread": 123,
      "automaticallyResolved": true,
      "oneDayPriceChange": 123,
      "oneHourPriceChange": 123,
      "oneWeekPriceChange": 123,
      "oneMonthPriceChange": 123,
      "oneYearPriceChange": 123,
      "lastTradePrice": 123,
      "bestBid": 123,
      "bestAsk": 123,
      "automaticallyActive": true,
      "clearBookOnStart": true,
      "chartColor": "<string>",
      "seriesColor": "<string>",
      "showGmpSeries": true,
      "showGmpOutcome": true,
      "manualActivation": true,
      "negRiskOther": true,
      "gameId": "<string>",
      "groupItemRange": "<string>",
      "sportsMarketType": "<string>",
      "line": 123,
      "umaResolutionStatuses": "<string>",
      "pendingDeployment": true,
      "deploying": true,
      "deployingTimestamp": "2023-11-07T05:31:56Z",
      "scheduledDeploymentTimestamp": "2023-11-07T05:31:56Z",
      "rfqEnabled": true,
      "eventStartTime": "2023-11-07T05:31:56Z"
    }
  ],
  "series": [
    {
      "id": "<string>",
      "ticker": "<string>",
      "slug": "<string>",
      "title": "<string>",
      "subtitle": "<string>",
      "seriesType": "<string>",
      "recurrence": "<string>",
      "description": "<string>",
      "image": "<string>",
      "icon": "<string>",
      "layout": "<string>",
      "active": true,
      "closed": true,
      "archived": true,
      "new": true,
      "featured": true,
      "restricted": true,
      "isTemplate": true,
      "templateVariables": true,
      "publishedAt": "<string>",
      "createdBy": "<string>",
      "updatedBy": "<string>",
      "createdAt": "2023-11-07T05:31:56Z",
      "updatedAt": "2023-11-07T05:31:56Z",
      "commentsEnabled": true,
      "competitive": "<string>",
      "volume24hr": 123,
      "volume": 123,
      "liquidity": 123,
      "startDate": "2023-11-07T05:31:56Z",
      "pythTokenID": "<string>",
      "cgAssetName": "<string>",
      "score": 123,
      "events": "<array>",
      "collections": [
        {
          "id": "<string>",
          "ticker": "<string>",
          "slug": "<string>",
          "title": "<string>",
          "subtitle": "<string>",
          "collectionType": "<string>",
          "description": "<string>",
          "tags": "<string>",
          "image": "<string>",
          "icon": "<string>",
          "headerImage": "<string>",
          "layout": "<string>",
          "active": true,
          "closed": true,
          "archived": true,
          "new": true,
          "featured": true,
          "restricted": true,
          "isTemplate": true,
          "templateVariables": "<string>",
          "publishedAt": "<string>",
          "createdBy": "<string>",
          "updatedBy": "<string>",
          "createdAt": "2023-11-07T05:31:56Z",
          "updatedAt": "2023-11-07T05:31:56Z",
          "commentsEnabled": true,
          "imageOptimized": {
            "id": "<string>",
            "imageUrlSource": "<string>",
            "imageUrlOptimized": "<string>",
            "imageSizeKbSource": 123,
            "imageSizeKbOptimized": 123,
            "imageOptimizedComplete": true,
            "imageOptimizedLastUpdated": "<string>",
            "relID": 123,
            "field": "<string>",
            "relname": "<string>"
          },
          "iconOptimized": {
            "id": "<string>",
            "imageUrlSource": "<string>",
            "imageUrlOptimized": "<string>",
            "imageSizeKbSource": 123,
            "imageSizeKbOptimized": 123,
            "imageOptimizedComplete": true,
            "imageOptimizedLastUpdated": "<string>",
            "relID": 123,
            "field": "<string>",
            "relname": "<string>"
          },
          "headerImageOptimized": {
            "id": "<string>",
            "imageUrlSource": "<string>",
            "imageUrlOptimized": "<string>",
            "imageSizeKbSource": 123,
            "imageSizeKbOptimized": 123,
            "imageOptimizedComplete": true,
            "imageOptimizedLastUpdated": "<string>",
            "relID": 123,
            "field": "<string>",
            "relname": "<string>"
          }
        }
      ],
      "categories": [
        {
          "id": "<string>",
          "label": "<string>",
          "parentCategory": "<string>",
          "slug": "<string>",
          "publishedAt": "<string>",
          "createdBy": "<string>",
          "updatedBy": "<string>",
          "createdAt": "2023-11-07T05:31:56Z",
          "updatedAt": "2023-11-07T05:31:56Z"
        }
      ],
      "tags": [
        {
          "id": "<string>",
          "label": "<string>",
          "slug": "<string>",
          "forceShow": true,
          "publishedAt": "<string>",
          "createdBy": 123,
          "updatedBy": 123,
          "createdAt": "2023-11-07T05:31:56Z",
          "updatedAt": "2023-11-07T05:31:56Z",
          "forceHide": true,
          "isCarousel": true
        }
      ],
      "commentCount": 123,
      "chats": [
        {
          "id": "<string>",
          "channelId": "<string>",
          "channelName": "<string>",
          "channelImage": "<string>",
          "live": true,
          "startTime": "2023-11-07T05:31:56Z",
          "endTime": "2023-11-07T05:31:56Z"
        }
      ]
    }
  ],
  "categories": [
    {
      "id": "<string>",
      "label": "<string>",
      "parentCategory": "<string>",
      "slug": "<string>",
      "publishedAt": "<string>",
      "createdBy": "<string>",
      "updatedBy": "<string>",
      "createdAt": "2023-11-07T05:31:56Z",
      "updatedAt": "2023-11-07T05:31:56Z"
    }
  ],
  "collections": [
    {
      "id": "<string>",
      "ticker": "<string>",
      "slug": "<string>",
      "title": "<string>",
      "subtitle": "<string>",
      "collectionType": "<string>",
      "description": "<string>",
      "tags": "<string>",
      "image": "<string>",
      "icon": "<string>",
      "headerImage": "<string>",
      "layout": "<string>",
      "active": true,
      "closed": true,
      "archived": true,
      "new": true,
      "featured": true,
      "restricted": true,
      "isTemplate": true,
      "templateVariables": "<string>",
      "publishedAt": "<string>",
      "createdBy": "<string>",
      "updatedBy": "<string>",
      "createdAt": "2023-11-07T05:31:56Z",
      "updatedAt": "2023-11-07T05:31:56Z",
      "commentsEnabled": true,
      "imageOptimized": {
        "id": "<string>",
        "imageUrlSource": "<string>",
        "imageUrlOptimized": "<string>",
        "imageSizeKbSource": 123,
        "imageSizeKbOptimized": 123,
        "imageOptimizedComplete": true,
        "imageOptimizedLastUpdated": "<string>",
        "relID": 123,
        "field": "<string>",
        "relname": "<string>"
      },
      "iconOptimized": {
        "id": "<string>",
        "imageUrlSource": "<string>",
        "imageUrlOptimized": "<string>",
        "imageSizeKbSource": 123,
        "imageSizeKbOptimized": 123,
        "imageOptimizedComplete": true,
        "imageOptimizedLastUpdated": "<string>",
        "relID": 123,
        "field": "<string>",
        "relname": "<string>"
      },
      "headerImageOptimized": {
        "id": "<string>",
        "imageUrlSource": "<string>",
        "imageUrlOptimized": "<string>",
        "imageSizeKbSource": 123,
        "imageSizeKbOptimized": 123,
        "imageOptimizedComplete": true,
        "imageOptimizedLastUpdated": "<string>",
        "relID": 123,
        "field": "<string>",
        "relname": "<string>"
      }
    }
  ],
  "tags": [
    {
      "id": "<string>",
      "label": "<string>",
      "slug": "<string>",
      "forceShow": true,
      "publishedAt": "<string>",
      "createdBy": 123,
      "updatedBy": 123,
      "createdAt": "2023-11-07T05:31:56Z",
      "updatedAt": "2023-11-07T05:31:56Z",
      "forceHide": true,
      "isCarousel": true
    }
  ],
  "cyom": true,
  "closedTime": "2023-11-07T05:31:56Z",
  "showAllOutcomes": true,
  "showMarketImages": true,
  "automaticallyResolved": true,
  "enableNegRisk": true,
  "automaticallyActive": true,
  "eventDate": "<string>",
  "startTime": "2023-11-07T05:31:56Z",
  "eventWeek": 123,
  "seriesSlug": "<string>",
  "score": "<string>",
  "elapsed": "<string>",
  "period": "<string>",
  "live": true,
  "ended": true,
  "finishedTimestamp": "2023-11-07T05:31:56Z",
  "gmpChartMode": "<string>",
  "eventCreators": [
    {
      "id": "<string>",
      "creatorName": "<string>",
      "creatorHandle": "<string>",
      "creatorUrl": "<string>",
      "creatorImage": "<string>",
      "createdAt": "2023-11-07T05:31:56Z",
      "updatedAt": "2023-11-07T05:31:56Z"
    }
  ],
  "tweetCount": 123,
  "chats": [
    {
      "id": "<string>",
      "channelId": "<string>",
      "channelName": "<string>",
      "channelImage": "<string>",
      "live": true,
      "startTime": "2023-11-07T05:31:56Z",
      "endTime": "2023-11-07T05:31:56Z"
    }
  ],
  "featuredOrder": 123,
  "estimateValue": true,
  "cantEstimate": true,
  "estimatedValue": "<string>",
  "templates": [
    {
      "id": "<string>",
      "eventTitle": "<string>",
      "eventSlug": "<string>",
      "eventImage": "<string>",
      "marketTitle": "<string>",
      "description": "<string>",
      "resolutionSource": "<string>",
      "negRisk": true,
      "sortBy": "<string>",
      "showMarketImages": true,
      "seriesSlug": "<string>",
      "outcomes": "<string>"
    }
  ],
  "spreadsMainLine": 123,
  "totalsMainLine": 123,
  "carouselMap": "<string>",
  "pendingDeployment": true,
  "deploying": true,
  "deployingTimestamp": "2023-11-07T05:31:56Z",
  "scheduledDeploymentTimestamp": "2023-11-07T05:31:56Z",
  "gameStatus": "<string>"
}


List markets

curl --request GET \
  --url https://gamma-api.polymarket.com/markets

200
[
  {
    "id": "<string>",
    "question": "<string>",
    "conditionId": "<string>",
    "slug": "<string>",
    "twitterCardImage": "<string>",
    "resolutionSource": "<string>",
    "endDate": "2023-11-07T05:31:56Z",
    "category": "<string>",
    "ammType": "<string>",
    "liquidity": "<string>",
    "sponsorName": "<string>",
    "sponsorImage": "<string>",
    "startDate": "2023-11-07T05:31:56Z",
    "xAxisValue": "<string>",
    "yAxisValue": "<string>",
    "denominationToken": "<string>",
    "fee": "<string>",
    "image": "<string>",
    "icon": "<string>",
    "lowerBound": "<string>",
    "upperBound": "<string>",
    "description": "<string>",
    "outcomes": "<string>",
    "outcomePrices": "<string>",
    "volume": "<string>",
    "active": true,
    "marketType": "<string>",
    "formatType": "<string>",
    "lowerBoundDate": "<string>",
    "upperBoundDate": "<string>",
    "closed": true,
    "marketMakerAddress": "<string>",
    "createdBy": 123,
    "updatedBy": 123,
    "createdAt": "2023-11-07T05:31:56Z",
    "updatedAt": "2023-11-07T05:31:56Z",
    "closedTime": "<string>",
    "wideFormat": true,
    "new": true,
    "mailchimpTag": "<string>",
    "featured": true,
    "archived": true,
    "resolvedBy": "<string>",
    "restricted": true,
    "marketGroup": 123,
    "groupItemTitle": "<string>",
    "groupItemThreshold": "<string>",
    "questionID": "<string>",
    "umaEndDate": "<string>",
    "enableOrderBook": true,
    "orderPriceMinTickSize": 123,
    "orderMinSize": 123,
    "umaResolutionStatus": "<string>",
    "curationOrder": 123,
    "volumeNum": 123,
    "liquidityNum": 123,
    "endDateIso": "<string>",
    "startDateIso": "<string>",
    "umaEndDateIso": "<string>",
    "hasReviewedDates": true,
    "readyForCron": true,
    "commentsEnabled": true,
    "volume24hr": 123,
    "volume1wk": 123,
    "volume1mo": 123,
    "volume1yr": 123,
    "gameStartTime": "<string>",
    "secondsDelay": 123,
    "clobTokenIds": "<string>",
    "disqusThread": "<string>",
    "shortOutcomes": "<string>",
    "teamAID": "<string>",
    "teamBID": "<string>",
    "umaBond": "<string>",
    "umaReward": "<string>",
    "fpmmLive": true,
    "volume24hrAmm": 123,
    "volume1wkAmm": 123,
    "volume1moAmm": 123,
    "volume1yrAmm": 123,
    "volume24hrClob": 123,
    "volume1wkClob": 123,
    "volume1moClob": 123,
    "volume1yrClob": 123,
    "volumeAmm": 123,
    "volumeClob": 123,
    "liquidityAmm": 123,
    "liquidityClob": 123,
    "makerBaseFee": 123,
    "takerBaseFee": 123,
    "customLiveness": 123,
    "acceptingOrders": true,
    "notificationsEnabled": true,
    "score": 123,
    "imageOptimized": {
      "id": "<string>",
      "imageUrlSource": "<string>",
      "imageUrlOptimized": "<string>",
      "imageSizeKbSource": 123,
      "imageSizeKbOptimized": 123,
      "imageOptimizedComplete": true,
      "imageOptimizedLastUpdated": "<string>",
      "relID": 123,
      "field": "<string>",
      "relname": "<string>"
    },
    "iconOptimized": {
      "id": "<string>",
      "imageUrlSource": "<string>",
      "imageUrlOptimized": "<string>",
      "imageSizeKbSource": 123,
      "imageSizeKbOptimized": 123,
      "imageOptimizedComplete": true,
      "imageOptimizedLastUpdated": "<string>",
      "relID": 123,
      "field": "<string>",
      "relname": "<string>"
    },
    "events": [
      {
        "id": "<string>",
        "ticker": "<string>",
        "slug": "<string>",
        "title": "<string>",
        "subtitle": "<string>",
        "description": "<string>",
        "resolutionSource": "<string>",
        "startDate": "2023-11-07T05:31:56Z",
        "creationDate": "2023-11-07T05:31:56Z",
        "endDate": "2023-11-07T05:31:56Z",
        "image": "<string>",
        "icon": "<string>",
        "active": true,
        "closed": true,
        "archived": true,
        "new": true,
        "featured": true,
        "restricted": true,
        "liquidity": 123,
        "volume": 123,
        "openInterest": 123,
        "sortBy": "<string>",
        "category": "<string>",
        "subcategory": "<string>",
        "isTemplate": true,
        "templateVariables": "<string>",
        "published_at": "<string>",
        "createdBy": "<string>",
        "updatedBy": "<string>",
        "createdAt": "2023-11-07T05:31:56Z",
        "updatedAt": "2023-11-07T05:31:56Z",
        "commentsEnabled": true,
        "competitive": 123,
        "volume24hr": 123,
        "volume1wk": 123,
        "volume1mo": 123,
        "volume1yr": 123,
        "featuredImage": "<string>",
        "disqusThread": "<string>",
        "parentEvent": "<string>",
        "enableOrderBook": true,
        "liquidityAmm": 123,
        "liquidityClob": 123,
        "negRisk": true,
        "negRiskMarketID": "<string>",
        "negRiskFeeBips": 123,
        "commentCount": 123,
        "imageOptimized": {
          "id": "<string>",
          "imageUrlSource": "<string>",
          "imageUrlOptimized": "<string>",
          "imageSizeKbSource": 123,
          "imageSizeKbOptimized": 123,
          "imageOptimizedComplete": true,
          "imageOptimizedLastUpdated": "<string>",
          "relID": 123,
          "field": "<string>",
          "relname": "<string>"
        },
        "iconOptimized": {
          "id": "<string>",
          "imageUrlSource": "<string>",
          "imageUrlOptimized": "<string>",
          "imageSizeKbSource": 123,
          "imageSizeKbOptimized": 123,
          "imageOptimizedComplete": true,
          "imageOptimizedLastUpdated": "<string>",
          "relID": 123,
          "field": "<string>",
          "relname": "<string>"
        },
        "featuredImageOptimized": {
          "id": "<string>",
          "imageUrlSource": "<string>",
          "imageUrlOptimized": "<string>",
          "imageSizeKbSource": 123,
          "imageSizeKbOptimized": 123,
          "imageOptimizedComplete": true,
          "imageOptimizedLastUpdated": "<string>",
          "relID": 123,
          "field": "<string>",
          "relname": "<string>"
        },
        "subEvents": [
          "<string>"
        ],
        "markets": "<array>",
        "series": [
          {
            "id": "<string>",
            "ticker": "<string>",
            "slug": "<string>",
            "title": "<string>",
            "subtitle": "<string>",
            "seriesType": "<string>",
            "recurrence": "<string>",
            "description": "<string>",
            "image": "<string>",
            "icon": "<string>",
            "layout": "<string>",
            "active": true,
            "closed": true,
            "archived": true,
            "new": true,
            "featured": true,
            "restricted": true,
            "isTemplate": true,
            "templateVariables": true,
            "publishedAt": "<string>",
            "createdBy": "<string>",
            "updatedBy": "<string>",
            "createdAt": "2023-11-07T05:31:56Z",
            "updatedAt": "2023-11-07T05:31:56Z",
            "commentsEnabled": true,
            "competitive": "<string>",
            "volume24hr": 123,
            "volume": 123,
            "liquidity": 123,
            "startDate": "2023-11-07T05:31:56Z",
            "pythTokenID": "<string>",
            "cgAssetName": "<string>",
            "score": 123,
            "events": "<array>",
            "collections": [
              {
                "id": "<string>",
                "ticker": "<string>",
                "slug": "<string>",
                "title": "<string>",
                "subtitle": "<string>",
                "collectionType": "<string>",
                "description": "<string>",
                "tags": "<string>",
                "image": "<string>",
                "icon": "<string>",
                "headerImage": "<string>",
                "layout": "<string>",
                "active": true,
                "closed": true,
                "archived": true,
                "new": true,
                "featured": true,
                "restricted": true,
                "isTemplate": true,
                "templateVariables": "<string>",
                "publishedAt": "<string>",
                "createdBy": "<string>",
                "updatedBy": "<string>",
                "createdAt": "2023-11-07T05:31:56Z",
                "updatedAt": "2023-11-07T05:31:56Z",
                "commentsEnabled": true,
                "imageOptimized": {
                  "id": "<string>",
                  "imageUrlSource": "<string>",
                  "imageUrlOptimized": "<string>",
                  "imageSizeKbSource": 123,
                  "imageSizeKbOptimized": 123,
                  "imageOptimizedComplete": true,
                  "imageOptimizedLastUpdated": "<string>",
                  "relID": 123,
                  "field": "<string>",
                  "relname": "<string>"
                },
                "iconOptimized": {
                  "id": "<string>",
                  "imageUrlSource": "<string>",
                  "imageUrlOptimized": "<string>",
                  "imageSizeKbSource": 123,
                  "imageSizeKbOptimized": 123,
                  "imageOptimizedComplete": true,
                  "imageOptimizedLastUpdated": "<string>",
                  "relID": 123,
                  "field": "<string>",
                  "relname": "<string>"
                },
                "headerImageOptimized": {
                  "id": "<string>",
                  "imageUrlSource": "<string>",
                  "imageUrlOptimized": "<string>",
                  "imageSizeKbSource": 123,
                  "imageSizeKbOptimized": 123,
                  "imageOptimizedComplete": true,
                  "imageOptimizedLastUpdated": "<string>",
                  "relID": 123,
                  "field": "<string>",
                  "relname": "<string>"
                }
              }
            ],
            "categories": [
              {
                "id": "<string>",
                "label": "<string>",
                "parentCategory": "<string>",
                "slug": "<string>",
                "publishedAt": "<string>",
                "createdBy": "<string>",
                "updatedBy": "<string>",
                "createdAt": "2023-11-07T05:31:56Z",
                "updatedAt": "2023-11-07T05:31:56Z"
              }
            ],
            "tags": [
              {
                "id": "<string>",
                "label": "<string>",
                "slug": "<string>",
                "forceShow": true,
                "publishedAt": "<string>",
                "createdBy": 123,
                "updatedBy": 123,
                "createdAt": "2023-11-07T05:31:56Z",
                "updatedAt": "2023-11-07T05:31:56Z",
                "forceHide": true,
                "isCarousel": true
              }
            ],
            "commentCount": 123,
            "chats": [
              {
                "id": "<string>",
                "channelId": "<string>",
                "channelName": "<string>",
                "channelImage": "<string>",
                "live": true,
                "startTime": "2023-11-07T05:31:56Z",
                "endTime": "2023-11-07T05:31:56Z"
              }
            ]
          }
        ],
        "categories": [
          {
            "id": "<string>",
            "label": "<string>",
            "parentCategory": "<string>",
            "slug": "<string>",
            "publishedAt": "<string>",
            "createdBy": "<string>",
            "updatedBy": "<string>",
            "createdAt": "2023-11-07T05:31:56Z",
            "updatedAt": "2023-11-07T05:31:56Z"
          }
        ],
        "collections": [
          {
            "id": "<string>",
            "ticker": "<string>",
            "slug": "<string>",
            "title": "<string>",
            "subtitle": "<string>",
            "collectionType": "<string>",
            "description": "<string>",
            "tags": "<string>",
            "image": "<string>",
            "icon": "<string>",
            "headerImage": "<string>",
            "layout": "<string>",
            "active": true,
            "closed": true,
            "archived": true,
            "new": true,
            "featured": true,
            "restricted": true,
            "isTemplate": true,
            "templateVariables": "<string>",
            "publishedAt": "<string>",
            "createdBy": "<string>",
            "updatedBy": "<string>",
            "createdAt": "2023-11-07T05:31:56Z",
            "updatedAt": "2023-11-07T05:31:56Z",
            "commentsEnabled": true,
            "imageOptimized": {
              "id": "<string>",
              "imageUrlSource": "<string>",
              "imageUrlOptimized": "<string>",
              "imageSizeKbSource": 123,
              "imageSizeKbOptimized": 123,
              "imageOptimizedComplete": true,
              "imageOptimizedLastUpdated": "<string>",
              "relID": 123,
              "field": "<string>",
              "relname": "<string>"
            },
            "iconOptimized": {
              "id": "<string>",
              "imageUrlSource": "<string>",
              "imageUrlOptimized": "<string>",
              "imageSizeKbSource": 123,
              "imageSizeKbOptimized": 123,
              "imageOptimizedComplete": true,
              "imageOptimizedLastUpdated": "<string>",
              "relID": 123,
              "field": "<string>",
              "relname": "<string>"
            },
            "headerImageOptimized": {
              "id": "<string>",
              "imageUrlSource": "<string>",
              "imageUrlOptimized": "<string>",
              "imageSizeKbSource": 123,
              "imageSizeKbOptimized": 123,
              "imageOptimizedComplete": true,
              "imageOptimizedLastUpdated": "<string>",
              "relID": 123,
              "field": "<string>",
              "relname": "<string>"
            }
          }
        ],
        "tags": [
          {
            "id": "<string>",
            "label": "<string>",
            "slug": "<string>",
            "forceShow": true,
            "publishedAt": "<string>",
            "createdBy": 123,
            "updatedBy": 123,
            "createdAt": "2023-11-07T05:31:56Z",
            "updatedAt": "2023-11-07T05:31:56Z",
            "forceHide": true,
            "isCarousel": true
          }
        ],
        "cyom": true,
        "closedTime": "2023-11-07T05:31:56Z",
        "showAllOutcomes": true,
        "showMarketImages": true,
        "automaticallyResolved": true,
        "enableNegRisk": true,
        "automaticallyActive": true,
        "eventDate": "<string>",
        "startTime": "2023-11-07T05:31:56Z",
        "eventWeek": 123,
        "seriesSlug": "<string>",
        "score": "<string>",
        "elapsed": "<string>",
        "period": "<string>",
        "live": true,
        "ended": true,
        "finishedTimestamp": "2023-11-07T05:31:56Z",
        "gmpChartMode": "<string>",
        "eventCreators": [
          {
            "id": "<string>",
            "creatorName": "<string>",
            "creatorHandle": "<string>",
            "creatorUrl": "<string>",
            "creatorImage": "<string>",
            "createdAt": "2023-11-07T05:31:56Z",
            "updatedAt": "2023-11-07T05:31:56Z"
          }
        ],
        "tweetCount": 123,
        "chats": [
          {
            "id": "<string>",
            "channelId": "<string>",
            "channelName": "<string>",
            "channelImage": "<string>",
            "live": true,
            "startTime": "2023-11-07T05:31:56Z",
            "endTime": "2023-11-07T05:31:56Z"
          }
        ],
        "featuredOrder": 123,
        "estimateValue": true,
        "cantEstimate": true,
        "estimatedValue": "<string>",
        "templates": [
          {
            "id": "<string>",
            "eventTitle": "<string>",
            "eventSlug": "<string>",
            "eventImage": "<string>",
            "marketTitle": "<string>",
            "description": "<string>",
            "resolutionSource": "<string>",
            "negRisk": true,
            "sortBy": "<string>",
            "showMarketImages": true,
            "seriesSlug": "<string>",
            "outcomes": "<string>"
          }
        ],
        "spreadsMainLine": 123,
        "totalsMainLine": 123,
        "carouselMap": "<string>",
        "pendingDeployment": true,
        "deploying": true,
        "deployingTimestamp": "2023-11-07T05:31:56Z",
        "scheduledDeploymentTimestamp": "2023-11-07T05:31:56Z",
        "gameStatus": "<string>"
      }
    ],
    "categories": [
      {
        "id": "<string>",
        "label": "<string>",
        "parentCategory": "<string>",
        "slug": "<string>",
        "publishedAt": "<string>",
        "createdBy": "<string>",
        "updatedBy": "<string>",
        "createdAt": "2023-11-07T05:31:56Z",
        "updatedAt": "2023-11-07T05:31:56Z"
      }
    ],
    "tags": [
      {
        "id": "<string>",
        "label": "<string>",
        "slug": "<string>",
        "forceShow": true,
        "publishedAt": "<string>",
        "createdBy": 123,
        "updatedBy": 123,
        "createdAt": "2023-11-07T05:31:56Z",
        "updatedAt": "2023-11-07T05:31:56Z",
        "forceHide": true,
        "isCarousel": true
      }
    ],
    "creator": "<string>",
    "ready": true,
    "funded": true,
    "pastSlugs": "<string>",
    "readyTimestamp": "2023-11-07T05:31:56Z",
    "fundedTimestamp": "2023-11-07T05:31:56Z",
    "acceptingOrdersTimestamp": "2023-11-07T05:31:56Z",
    "competitive": 123,
    "rewardsMinSize": 123,
    "rewardsMaxSpread": 123,
    "spread": 123,
    "automaticallyResolved": true,
    "oneDayPriceChange": 123,
    "oneHourPriceChange": 123,
    "oneWeekPriceChange": 123,
    "oneMonthPriceChange": 123,
    "oneYearPriceChange": 123,
    "lastTradePrice": 123,
    "bestBid": 123,
    "bestAsk": 123,
    "automaticallyActive": true,
    "clearBookOnStart": true,
    "chartColor": "<string>",
    "seriesColor": "<string>",
    "showGmpSeries": true,
    "showGmpOutcome": true,
    "manualActivation": true,
    "negRiskOther": true,
    "gameId": "<string>",
    "groupItemRange": "<string>",
    "sportsMarketType": "<string>",
    "line": 123,
    "umaResolutionStatuses": "<string>",
    "pendingDeployment": true,
    "deploying": true,
    "deployingTimestamp": "2023-11-07T05:31:56Z",
    "scheduledDeploymentTimestamp": "2023-11-07T05:31:56Z",
    "rfqEnabled": true,
    "eventStartTime": "2023-11-07T05:31:56Z"
  }
]

Get market by id

curl --request GET \
  --url https://gamma-api.polymarket.com/markets/{id}

200

404
{
  "id": "<string>",
  "question": "<string>",
  "conditionId": "<string>",
  "slug": "<string>",
  "twitterCardImage": "<string>",
  "resolutionSource": "<string>",
  "endDate": "2023-11-07T05:31:56Z",
  "category": "<string>",
  "ammType": "<string>",
  "liquidity": "<string>",
  "sponsorName": "<string>",
  "sponsorImage": "<string>",
  "startDate": "2023-11-07T05:31:56Z",
  "xAxisValue": "<string>",
  "yAxisValue": "<string>",
  "denominationToken": "<string>",
  "fee": "<string>",
  "image": "<string>",
  "icon": "<string>",
  "lowerBound": "<string>",
  "upperBound": "<string>",
  "description": "<string>",
  "outcomes": "<string>",
  "outcomePrices": "<string>",
  "volume": "<string>",
  "active": true,
  "marketType": "<string>",
  "formatType": "<string>",
  "lowerBoundDate": "<string>",
  "upperBoundDate": "<string>",
  "closed": true,
  "marketMakerAddress": "<string>",
  "createdBy": 123,
  "updatedBy": 123,
  "createdAt": "2023-11-07T05:31:56Z",
  "updatedAt": "2023-11-07T05:31:56Z",
  "closedTime": "<string>",
  "wideFormat": true,
  "new": true,
  "mailchimpTag": "<string>",
  "featured": true,
  "archived": true,
  "resolvedBy": "<string>",
  "restricted": true,
  "marketGroup": 123,
  "groupItemTitle": "<string>",
  "groupItemThreshold": "<string>",
  "questionID": "<string>",
  "umaEndDate": "<string>",
  "enableOrderBook": true,
  "orderPriceMinTickSize": 123,
  "orderMinSize": 123,
  "umaResolutionStatus": "<string>",
  "curationOrder": 123,
  "volumeNum": 123,
  "liquidityNum": 123,
  "endDateIso": "<string>",
  "startDateIso": "<string>",
  "umaEndDateIso": "<string>",
  "hasReviewedDates": true,
  "readyForCron": true,
  "commentsEnabled": true,
  "volume24hr": 123,
  "volume1wk": 123,
  "volume1mo": 123,
  "volume1yr": 123,
  "gameStartTime": "<string>",
  "secondsDelay": 123,
  "clobTokenIds": "<string>",
  "disqusThread": "<string>",
  "shortOutcomes": "<string>",
  "teamAID": "<string>",
  "teamBID": "<string>",
  "umaBond": "<string>",
  "umaReward": "<string>",
  "fpmmLive": true,
  "volume24hrAmm": 123,
  "volume1wkAmm": 123,
  "volume1moAmm": 123,
  "volume1yrAmm": 123,
  "volume24hrClob": 123,
  "volume1wkClob": 123,
  "volume1moClob": 123,
  "volume1yrClob": 123,
  "volumeAmm": 123,
  "volumeClob": 123,
  "liquidityAmm": 123,
  "liquidityClob": 123,
  "makerBaseFee": 123,
  "takerBaseFee": 123,
  "customLiveness": 123,
  "acceptingOrders": true,
  "notificationsEnabled": true,
  "score": 123,
  "imageOptimized": {
    "id": "<string>",
    "imageUrlSource": "<string>",
    "imageUrlOptimized": "<string>",
    "imageSizeKbSource": 123,
    "imageSizeKbOptimized": 123,
    "imageOptimizedComplete": true,
    "imageOptimizedLastUpdated": "<string>",
    "relID": 123,
    "field": "<string>",
    "relname": "<string>"
  },
  "iconOptimized": {
    "id": "<string>",
    "imageUrlSource": "<string>",
    "imageUrlOptimized": "<string>",
    "imageSizeKbSource": 123,
    "imageSizeKbOptimized": 123,
    "imageOptimizedComplete": true,
    "imageOptimizedLastUpdated": "<string>",
    "relID": 123,
    "field": "<string>",
    "relname": "<string>"
  },
  "events": [
    {
      "id": "<string>",
      "ticker": "<string>",
      "slug": "<string>",
      "title": "<string>",
      "subtitle": "<string>",
      "description": "<string>",
      "resolutionSource": "<string>",
      "startDate": "2023-11-07T05:31:56Z",
      "creationDate": "2023-11-07T05:31:56Z",
      "endDate": "2023-11-07T05:31:56Z",
      "image": "<string>",
      "icon": "<string>",
      "active": true,
      "closed": true,
      "archived": true,
      "new": true,
      "featured": true,
      "restricted": true,
      "liquidity": 123,
      "volume": 123,
      "openInterest": 123,
      "sortBy": "<string>",
      "category": "<string>",
      "subcategory": "<string>",
      "isTemplate": true,
      "templateVariables": "<string>",
      "published_at": "<string>",
      "createdBy": "<string>",
      "updatedBy": "<string>",
      "createdAt": "2023-11-07T05:31:56Z",
      "updatedAt": "2023-11-07T05:31:56Z",
      "commentsEnabled": true,
      "competitive": 123,
      "volume24hr": 123,
      "volume1wk": 123,
      "volume1mo": 123,
      "volume1yr": 123,
      "featuredImage": "<string>",
      "disqusThread": "<string>",
      "parentEvent": "<string>",
      "enableOrderBook": true,
      "liquidityAmm": 123,
      "liquidityClob": 123,
      "negRisk": true,
      "negRiskMarketID": "<string>",
      "negRiskFeeBips": 123,
      "commentCount": 123,
      "imageOptimized": {
        "id": "<string>",
        "imageUrlSource": "<string>",
        "imageUrlOptimized": "<string>",
        "imageSizeKbSource": 123,
        "imageSizeKbOptimized": 123,
        "imageOptimizedComplete": true,
        "imageOptimizedLastUpdated": "<string>",
        "relID": 123,
        "field": "<string>",
        "relname": "<string>"
      },
      "iconOptimized": {
        "id": "<string>",
        "imageUrlSource": "<string>",
        "imageUrlOptimized": "<string>",
        "imageSizeKbSource": 123,
        "imageSizeKbOptimized": 123,
        "imageOptimizedComplete": true,
        "imageOptimizedLastUpdated": "<string>",
        "relID": 123,
        "field": "<string>",
        "relname": "<string>"
      },
      "featuredImageOptimized": {
        "id": "<string>",
        "imageUrlSource": "<string>",
        "imageUrlOptimized": "<string>",
        "imageSizeKbSource": 123,
        "imageSizeKbOptimized": 123,
        "imageOptimizedComplete": true,
        "imageOptimizedLastUpdated": "<string>",
        "relID": 123,
        "field": "<string>",
        "relname": "<string>"
      },
      "subEvents": [
        "<string>"
      ],
      "markets": "<array>",
      "series": [
        {
          "id": "<string>",
          "ticker": "<string>",
          "slug": "<string>",
          "title": "<string>",
          "subtitle": "<string>",
          "seriesType": "<string>",
          "recurrence": "<string>",
          "description": "<string>",
          "image": "<string>",
          "icon": "<string>",
          "layout": "<string>",
          "active": true,
          "closed": true,
          "archived": true,
          "new": true,
          "featured": true,
          "restricted": true,
          "isTemplate": true,
          "templateVariables": true,
          "publishedAt": "<string>",
          "createdBy": "<string>",
          "updatedBy": "<string>",
          "createdAt": "2023-11-07T05:31:56Z",
          "updatedAt": "2023-11-07T05:31:56Z",
          "commentsEnabled": true,
          "competitive": "<string>",
          "volume24hr": 123,
          "volume": 123,
          "liquidity": 123,
          "startDate": "2023-11-07T05:31:56Z",
          "pythTokenID": "<string>",
          "cgAssetName": "<string>",
          "score": 123,
          "events": "<array>",
          "collections": [
            {
              "id": "<string>",
              "ticker": "<string>",
              "slug": "<string>",
              "title": "<string>",
              "subtitle": "<string>",
              "collectionType": "<string>",
              "description": "<string>",
              "tags": "<string>",
              "image": "<string>",
              "icon": "<string>",
              "headerImage": "<string>",
              "layout": "<string>",
              "active": true,
              "closed": true,
              "archived": true,
              "new": true,
              "featured": true,
              "restricted": true,
              "isTemplate": true,
              "templateVariables": "<string>",
              "publishedAt": "<string>",
              "createdBy": "<string>",
              "updatedBy": "<string>",
              "createdAt": "2023-11-07T05:31:56Z",
              "updatedAt": "2023-11-07T05:31:56Z",
              "commentsEnabled": true,
              "imageOptimized": {
                "id": "<string>",
                "imageUrlSource": "<string>",
                "imageUrlOptimized": "<string>",
                "imageSizeKbSource": 123,
                "imageSizeKbOptimized": 123,
                "imageOptimizedComplete": true,
                "imageOptimizedLastUpdated": "<string>",
                "relID": 123,
                "field": "<string>",
                "relname": "<string>"
              },
              "iconOptimized": {
                "id": "<string>",
                "imageUrlSource": "<string>",
                "imageUrlOptimized": "<string>",
                "imageSizeKbSource": 123,
                "imageSizeKbOptimized": 123,
                "imageOptimizedComplete": true,
                "imageOptimizedLastUpdated": "<string>",
                "relID": 123,
                "field": "<string>",
                "relname": "<string>"
              },
              "headerImageOptimized": {
                "id": "<string>",
                "imageUrlSource": "<string>",
                "imageUrlOptimized": "<string>",
                "imageSizeKbSource": 123,
                "imageSizeKbOptimized": 123,
                "imageOptimizedComplete": true,
                "imageOptimizedLastUpdated": "<string>",
                "relID": 123,
                "field": "<string>",
                "relname": "<string>"
              }
            }
          ],
          "categories": [
            {
              "id": "<string>",
              "label": "<string>",
              "parentCategory": "<string>",
              "slug": "<string>",
              "publishedAt": "<string>",
              "createdBy": "<string>",
              "updatedBy": "<string>",
              "createdAt": "2023-11-07T05:31:56Z",
              "updatedAt": "2023-11-07T05:31:56Z"
            }
          ],
          "tags": [
            {
              "id": "<string>",
              "label": "<string>",
              "slug": "<string>",
              "forceShow": true,
              "publishedAt": "<string>",
              "createdBy": 123,
              "updatedBy": 123,
              "createdAt": "2023-11-07T05:31:56Z",
              "updatedAt": "2023-11-07T05:31:56Z",
              "forceHide": true,
              "isCarousel": true
            }
          ],
          "commentCount": 123,
          "chats": [
            {
              "id": "<string>",
              "channelId": "<string>",
              "channelName": "<string>",
              "channelImage": "<string>",
              "live": true,
              "startTime": "2023-11-07T05:31:56Z",
              "endTime": "2023-11-07T05:31:56Z"
            }
          ]
        }
      ],
      "categories": [
        {
          "id": "<string>",
          "label": "<string>",
          "parentCategory": "<string>",
          "slug": "<string>",
          "publishedAt": "<string>",
          "createdBy": "<string>",
          "updatedBy": "<string>",
          "createdAt": "2023-11-07T05:31:56Z",
          "updatedAt": "2023-11-07T05:31:56Z"
        }
      ],
      "collections": [
        {
          "id": "<string>",
          "ticker": "<string>",
          "slug": "<string>",
          "title": "<string>",
          "subtitle": "<string>",
          "collectionType": "<string>",
          "description": "<string>",
          "tags": "<string>",
          "image": "<string>",
          "icon": "<string>",
          "headerImage": "<string>",
          "layout": "<string>",
          "active": true,
          "closed": true,
          "archived": true,
          "new": true,
          "featured": true,
          "restricted": true,
          "isTemplate": true,
          "templateVariables": "<string>",
          "publishedAt": "<string>",
          "createdBy": "<string>",
          "updatedBy": "<string>",
          "createdAt": "2023-11-07T05:31:56Z",
          "updatedAt": "2023-11-07T05:31:56Z",
          "commentsEnabled": true,
          "imageOptimized": {
            "id": "<string>",
            "imageUrlSource": "<string>",
            "imageUrlOptimized": "<string>",
            "imageSizeKbSource": 123,
            "imageSizeKbOptimized": 123,
            "imageOptimizedComplete": true,
            "imageOptimizedLastUpdated": "<string>",
            "relID": 123,
            "field": "<string>",
            "relname": "<string>"
          },
          "iconOptimized": {
            "id": "<string>",
            "imageUrlSource": "<string>",
            "imageUrlOptimized": "<string>",
            "imageSizeKbSource": 123,
            "imageSizeKbOptimized": 123,
            "imageOptimizedComplete": true,
            "imageOptimizedLastUpdated": "<string>",
            "relID": 123,
            "field": "<string>",
            "relname": "<string>"
          },
          "headerImageOptimized": {
            "id": "<string>",
            "imageUrlSource": "<string>",
            "imageUrlOptimized": "<string>",
            "imageSizeKbSource": 123,
            "imageSizeKbOptimized": 123,
            "imageOptimizedComplete": true,
            "imageOptimizedLastUpdated": "<string>",
            "relID": 123,
            "field": "<string>",
            "relname": "<string>"
          }
        }
      ],
      "tags": [
        {
          "id": "<string>",
          "label": "<string>",
          "slug": "<string>",
          "forceShow": true,
          "publishedAt": "<string>",
          "createdBy": 123,
          "updatedBy": 123,
          "createdAt": "2023-11-07T05:31:56Z",
          "updatedAt": "2023-11-07T05:31:56Z",
          "forceHide": true,
          "isCarousel": true
        }
      ],
      "cyom": true,
      "closedTime": "2023-11-07T05:31:56Z",
      "showAllOutcomes": true,
      "showMarketImages": true,
      "automaticallyResolved": true,
      "enableNegRisk": true,
      "automaticallyActive": true,
      "eventDate": "<string>",
      "startTime": "2023-11-07T05:31:56Z",
      "eventWeek": 123,
      "seriesSlug": "<string>",
      "score": "<string>",
      "elapsed": "<string>",
      "period": "<string>",
      "live": true,
      "ended": true,
      "finishedTimestamp": "2023-11-07T05:31:56Z",
      "gmpChartMode": "<string>",
      "eventCreators": [
        {
          "id": "<string>",
          "creatorName": "<string>",
          "creatorHandle": "<string>",
          "creatorUrl": "<string>",
          "creatorImage": "<string>",
          "createdAt": "2023-11-07T05:31:56Z",
          "updatedAt": "2023-11-07T05:31:56Z"
        }
      ],
      "tweetCount": 123,
      "chats": [
        {
          "id": "<string>",
          "channelId": "<string>",
          "channelName": "<string>",
          "channelImage": "<string>",
          "live": true,
          "startTime": "2023-11-07T05:31:56Z",
          "endTime": "2023-11-07T05:31:56Z"
        }
      ],
      "featuredOrder": 123,
      "estimateValue": true,
      "cantEstimate": true,
      "estimatedValue": "<string>",
      "templates": [
        {
          "id": "<string>",
          "eventTitle": "<string>",
          "eventSlug": "<string>",
          "eventImage": "<string>",
          "marketTitle": "<string>",
          "description": "<string>",
          "resolutionSource": "<string>",
          "negRisk": true,
          "sortBy": "<string>",
          "showMarketImages": true,
          "seriesSlug": "<string>",
          "outcomes": "<string>"
        }
      ],
      "spreadsMainLine": 123,
      "totalsMainLine": 123,
      "carouselMap": "<string>",
      "pendingDeployment": true,
      "deploying": true,
      "deployingTimestamp": "2023-11-07T05:31:56Z",
      "scheduledDeploymentTimestamp": "2023-11-07T05:31:56Z",
      "gameStatus": "<string>"
    }
  ],
  "categories": [
    {
      "id": "<string>",
      "label": "<string>",
      "parentCategory": "<string>",
      "slug": "<string>",
      "publishedAt": "<string>",
      "createdBy": "<string>",
      "updatedBy": "<string>",
      "createdAt": "2023-11-07T05:31:56Z",
      "updatedAt": "2023-11-07T05:31:56Z"
    }
  ],
  "tags": [
    {
      "id": "<string>",
      "label": "<string>",
      "slug": "<string>",
      "forceShow": true,
      "publishedAt": "<string>",
      "createdBy": 123,
      "updatedBy": 123,
      "createdAt": "2023-11-07T05:31:56Z",
      "updatedAt": "2023-11-07T05:31:56Z",
      "forceHide": true,
      "isCarousel": true
    }
  ],
  "creator": "<string>",
  "ready": true,
  "funded": true,
  "pastSlugs": "<string>",
  "readyTimestamp": "2023-11-07T05:31:56Z",
  "fundedTimestamp": "2023-11-07T05:31:56Z",
  "acceptingOrdersTimestamp": "2023-11-07T05:31:56Z",
  "competitive": 123,
  "rewardsMinSize": 123,
  "rewardsMaxSpread": 123,
  "spread": 123,
  "automaticallyResolved": true,
  "oneDayPriceChange": 123,
  "oneHourPriceChange": 123,
  "oneWeekPriceChange": 123,
  "oneMonthPriceChange": 123,
  "oneYearPriceChange": 123,
  "lastTradePrice": 123,
  "bestBid": 123,
  "bestAsk": 123,
  "automaticallyActive": true,
  "clearBookOnStart": true,
  "chartColor": "<string>",
  "seriesColor": "<string>",
  "showGmpSeries": true,
  "showGmpOutcome": true,
  "manualActivation": true,
  "negRiskOther": true,
  "gameId": "<string>",
  "groupItemRange": "<string>",
  "sportsMarketType": "<string>",
  "line": 123,
  "umaResolutionStatuses": "<string>",
  "pendingDeployment": true,
  "deploying": true,
  "deployingTimestamp": "2023-11-07T05:31:56Z",
  "scheduledDeploymentTimestamp": "2023-11-07T05:31:56Z",
  "rfqEnabled": true,
  "eventStartTime": "2023-11-07T05:31:56Z"
}

Get market tags by id

curl --request GET \
  --url https://gamma-api.polymarket.com/markets/{id}/tags

200

404
[
  {
    "id": "<string>",
    "label": "<string>",
    "slug": "<string>",
    "forceShow": true,
    "publishedAt": "<string>",
    "createdBy": 123,
    "updatedBy": 123,
    "createdAt": "2023-11-07T05:31:56Z",
    "updatedAt": "2023-11-07T05:31:56Z",
    "forceHide": true,
    "isCarousel": true
  }
]


Get market by slug

curl --request GET \
  --url https://gamma-api.polymarket.com/markets/slug/{slug}

200

404
{
  "id": "<string>",
  "question": "<string>",
  "conditionId": "<string>",
  "slug": "<string>",
  "twitterCardImage": "<string>",
  "resolutionSource": "<string>",
  "endDate": "2023-11-07T05:31:56Z",
  "category": "<string>",
  "ammType": "<string>",
  "liquidity": "<string>",
  "sponsorName": "<string>",
  "sponsorImage": "<string>",
  "startDate": "2023-11-07T05:31:56Z",
  "xAxisValue": "<string>",
  "yAxisValue": "<string>",
  "denominationToken": "<string>",
  "fee": "<string>",
  "image": "<string>",
  "icon": "<string>",
  "lowerBound": "<string>",
  "upperBound": "<string>",
  "description": "<string>",
  "outcomes": "<string>",
  "outcomePrices": "<string>",
  "volume": "<string>",
  "active": true,
  "marketType": "<string>",
  "formatType": "<string>",
  "lowerBoundDate": "<string>",
  "upperBoundDate": "<string>",
  "closed": true,
  "marketMakerAddress": "<string>",
  "createdBy": 123,
  "updatedBy": 123,
  "createdAt": "2023-11-07T05:31:56Z",
  "updatedAt": "2023-11-07T05:31:56Z",
  "closedTime": "<string>",
  "wideFormat": true,
  "new": true,
  "mailchimpTag": "<string>",
  "featured": true,
  "archived": true,
  "resolvedBy": "<string>",
  "restricted": true,
  "marketGroup": 123,
  "groupItemTitle": "<string>",
  "groupItemThreshold": "<string>",
  "questionID": "<string>",
  "umaEndDate": "<string>",
  "enableOrderBook": true,
  "orderPriceMinTickSize": 123,
  "orderMinSize": 123,
  "umaResolutionStatus": "<string>",
  "curationOrder": 123,
  "volumeNum": 123,
  "liquidityNum": 123,
  "endDateIso": "<string>",
  "startDateIso": "<string>",
  "umaEndDateIso": "<string>",
  "hasReviewedDates": true,
  "readyForCron": true,
  "commentsEnabled": true,
  "volume24hr": 123,
  "volume1wk": 123,
  "volume1mo": 123,
  "volume1yr": 123,
  "gameStartTime": "<string>",
  "secondsDelay": 123,
  "clobTokenIds": "<string>",
  "disqusThread": "<string>",
  "shortOutcomes": "<string>",
  "teamAID": "<string>",
  "teamBID": "<string>",
  "umaBond": "<string>",
  "umaReward": "<string>",
  "fpmmLive": true,
  "volume24hrAmm": 123,
  "volume1wkAmm": 123,
  "volume1moAmm": 123,
  "volume1yrAmm": 123,
  "volume24hrClob": 123,
  "volume1wkClob": 123,
  "volume1moClob": 123,
  "volume1yrClob": 123,
  "volumeAmm": 123,
  "volumeClob": 123,
  "liquidityAmm": 123,
  "liquidityClob": 123,
  "makerBaseFee": 123,
  "takerBaseFee": 123,
  "customLiveness": 123,
  "acceptingOrders": true,
  "notificationsEnabled": true,
  "score": 123,
  "imageOptimized": {
    "id": "<string>",
    "imageUrlSource": "<string>",
    "imageUrlOptimized": "<string>",
    "imageSizeKbSource": 123,
    "imageSizeKbOptimized": 123,
    "imageOptimizedComplete": true,
    "imageOptimizedLastUpdated": "<string>",
    "relID": 123,
    "field": "<string>",
    "relname": "<string>"
  },
  "iconOptimized": {
    "id": "<string>",
    "imageUrlSource": "<string>",
    "imageUrlOptimized": "<string>",
    "imageSizeKbSource": 123,
    "imageSizeKbOptimized": 123,
    "imageOptimizedComplete": true,
    "imageOptimizedLastUpdated": "<string>",
    "relID": 123,
    "field": "<string>",
    "relname": "<string>"
  },
  "events": [
    {
      "id": "<string>",
      "ticker": "<string>",
      "slug": "<string>",
      "title": "<string>",
      "subtitle": "<string>",
      "description": "<string>",
      "resolutionSource": "<string>",
      "startDate": "2023-11-07T05:31:56Z",
      "creationDate": "2023-11-07T05:31:56Z",
      "endDate": "2023-11-07T05:31:56Z",
      "image": "<string>",
      "icon": "<string>",
      "active": true,
      "closed": true,
      "archived": true,
      "new": true,
      "featured": true,
      "restricted": true,
      "liquidity": 123,
      "volume": 123,
      "openInterest": 123,
      "sortBy": "<string>",
      "category": "<string>",
      "subcategory": "<string>",
      "isTemplate": true,
      "templateVariables": "<string>",
      "published_at": "<string>",
      "createdBy": "<string>",
      "updatedBy": "<string>",
      "createdAt": "2023-11-07T05:31:56Z",
      "updatedAt": "2023-11-07T05:31:56Z",
      "commentsEnabled": true,
      "competitive": 123,
      "volume24hr": 123,
      "volume1wk": 123,
      "volume1mo": 123,
      "volume1yr": 123,
      "featuredImage": "<string>",
      "disqusThread": "<string>",
      "parentEvent": "<string>",
      "enableOrderBook": true,
      "liquidityAmm": 123,
      "liquidityClob": 123,
      "negRisk": true,
      "negRiskMarketID": "<string>",
      "negRiskFeeBips": 123,
      "commentCount": 123,
      "imageOptimized": {
        "id": "<string>",
        "imageUrlSource": "<string>",
        "imageUrlOptimized": "<string>",
        "imageSizeKbSource": 123,
        "imageSizeKbOptimized": 123,
        "imageOptimizedComplete": true,
        "imageOptimizedLastUpdated": "<string>",
        "relID": 123,
        "field": "<string>",
        "relname": "<string>"
      },
      "iconOptimized": {
        "id": "<string>",
        "imageUrlSource": "<string>",
        "imageUrlOptimized": "<string>",
        "imageSizeKbSource": 123,
        "imageSizeKbOptimized": 123,
        "imageOptimizedComplete": true,
        "imageOptimizedLastUpdated": "<string>",
        "relID": 123,
        "field": "<string>",
        "relname": "<string>"
      },
      "featuredImageOptimized": {
        "id": "<string>",
        "imageUrlSource": "<string>",
        "imageUrlOptimized": "<string>",
        "imageSizeKbSource": 123,
        "imageSizeKbOptimized": 123,
        "imageOptimizedComplete": true,
        "imageOptimizedLastUpdated": "<string>",
        "relID": 123,
        "field": "<string>",
        "relname": "<string>"
      },
      "subEvents": [
        "<string>"
      ],
      "markets": "<array>",
      "series": [
        {
          "id": "<string>",
          "ticker": "<string>",
          "slug": "<string>",
          "title": "<string>",
          "subtitle": "<string>",
          "seriesType": "<string>",
          "recurrence": "<string>",
          "description": "<string>",
          "image": "<string>",
          "icon": "<string>",
          "layout": "<string>",
          "active": true,
          "closed": true,
          "archived": true,
          "new": true,
          "featured": true,
          "restricted": true,
          "isTemplate": true,
          "templateVariables": true,
          "publishedAt": "<string>",
          "createdBy": "<string>",
          "updatedBy": "<string>",
          "createdAt": "2023-11-07T05:31:56Z",
          "updatedAt": "2023-11-07T05:31:56Z",
          "commentsEnabled": true,
          "competitive": "<string>",
          "volume24hr": 123,
          "volume": 123,
          "liquidity": 123,
          "startDate": "2023-11-07T05:31:56Z",
          "pythTokenID": "<string>",
          "cgAssetName": "<string>",
          "score": 123,
          "events": "<array>",
          "collections": [
            {
              "id": "<string>",
              "ticker": "<string>",
              "slug": "<string>",
              "title": "<string>",
              "subtitle": "<string>",
              "collectionType": "<string>",
              "description": "<string>",
              "tags": "<string>",
              "image": "<string>",
              "icon": "<string>",
              "headerImage": "<string>",
              "layout": "<string>",
              "active": true,
              "closed": true,
              "archived": true,
              "new": true,
              "featured": true,
              "restricted": true,
              "isTemplate": true,
              "templateVariables": "<string>",
              "publishedAt": "<string>",
              "createdBy": "<string>",
              "updatedBy": "<string>",
              "createdAt": "2023-11-07T05:31:56Z",
              "updatedAt": "2023-11-07T05:31:56Z",
              "commentsEnabled": true,
              "imageOptimized": {
                "id": "<string>",
                "imageUrlSource": "<string>",
                "imageUrlOptimized": "<string>",
                "imageSizeKbSource": 123,
                "imageSizeKbOptimized": 123,
                "imageOptimizedComplete": true,
                "imageOptimizedLastUpdated": "<string>",
                "relID": 123,
                "field": "<string>",
                "relname": "<string>"
              },
              "iconOptimized": {
                "id": "<string>",
                "imageUrlSource": "<string>",
                "imageUrlOptimized": "<string>",
                "imageSizeKbSource": 123,
                "imageSizeKbOptimized": 123,
                "imageOptimizedComplete": true,
                "imageOptimizedLastUpdated": "<string>",
                "relID": 123,
                "field": "<string>",
                "relname": "<string>"
              },
              "headerImageOptimized": {
                "id": "<string>",
                "imageUrlSource": "<string>",
                "imageUrlOptimized": "<string>",
                "imageSizeKbSource": 123,
                "imageSizeKbOptimized": 123,
                "imageOptimizedComplete": true,
                "imageOptimizedLastUpdated": "<string>",
                "relID": 123,
                "field": "<string>",
                "relname": "<string>"
              }
            }
          ],
          "categories": [
            {
              "id": "<string>",
              "label": "<string>",
              "parentCategory": "<string>",
              "slug": "<string>",
              "publishedAt": "<string>",
              "createdBy": "<string>",
              "updatedBy": "<string>",
              "createdAt": "2023-11-07T05:31:56Z",
              "updatedAt": "2023-11-07T05:31:56Z"
            }
          ],
          "tags": [
            {
              "id": "<string>",
              "label": "<string>",
              "slug": "<string>",
              "forceShow": true,
              "publishedAt": "<string>",
              "createdBy": 123,
              "updatedBy": 123,
              "createdAt": "2023-11-07T05:31:56Z",
              "updatedAt": "2023-11-07T05:31:56Z",
              "forceHide": true,
              "isCarousel": true
            }
          ],
          "commentCount": 123,
          "chats": [
            {
              "id": "<string>",
              "channelId": "<string>",
              "channelName": "<string>",
              "channelImage": "<string>",
              "live": true,
              "startTime": "2023-11-07T05:31:56Z",
              "endTime": "2023-11-07T05:31:56Z"
            }
          ]
        }
      ],
      "categories": [
        {
          "id": "<string>",
          "label": "<string>",
          "parentCategory": "<string>",
          "slug": "<string>",
          "publishedAt": "<string>",
          "createdBy": "<string>",
          "updatedBy": "<string>",
          "createdAt": "2023-11-07T05:31:56Z",
          "updatedAt": "2023-11-07T05:31:56Z"
        }
      ],
      "collections": [
        {
          "id": "<string>",
          "ticker": "<string>",
          "slug": "<string>",
          "title": "<string>",
          "subtitle": "<string>",
          "collectionType": "<string>",
          "description": "<string>",
          "tags": "<string>",
          "image": "<string>",
          "icon": "<string>",
          "headerImage": "<string>",
          "layout": "<string>",
          "active": true,
          "closed": true,
          "archived": true,
          "new": true,
          "featured": true,
          "restricted": true,
          "isTemplate": true,
          "templateVariables": "<string>",
          "publishedAt": "<string>",
          "createdBy": "<string>",
          "updatedBy": "<string>",
          "createdAt": "2023-11-07T05:31:56Z",
          "updatedAt": "2023-11-07T05:31:56Z",
          "commentsEnabled": true,
          "imageOptimized": {
            "id": "<string>",
            "imageUrlSource": "<string>",
            "imageUrlOptimized": "<string>",
            "imageSizeKbSource": 123,
            "imageSizeKbOptimized": 123,
            "imageOptimizedComplete": true,
            "imageOptimizedLastUpdated": "<string>",
            "relID": 123,
            "field": "<string>",
            "relname": "<string>"
          },
          "iconOptimized": {
            "id": "<string>",
            "imageUrlSource": "<string>",
            "imageUrlOptimized": "<string>",
            "imageSizeKbSource": 123,
            "imageSizeKbOptimized": 123,
            "imageOptimizedComplete": true,
            "imageOptimizedLastUpdated": "<string>",
            "relID": 123,
            "field": "<string>",
            "relname": "<string>"
          },
          "headerImageOptimized": {
            "id": "<string>",
            "imageUrlSource": "<string>",
            "imageUrlOptimized": "<string>",
            "imageSizeKbSource": 123,
            "imageSizeKbOptimized": 123,
            "imageOptimizedComplete": true,
            "imageOptimizedLastUpdated": "<string>",
            "relID": 123,
            "field": "<string>",
            "relname": "<string>"
          }
        }
      ],
      "tags": [
        {
          "id": "<string>",
          "label": "<string>",
          "slug": "<string>",
          "forceShow": true,
          "publishedAt": "<string>",
          "createdBy": 123,
          "updatedBy": 123,
          "createdAt": "2023-11-07T05:31:56Z",
          "updatedAt": "2023-11-07T05:31:56Z",
          "forceHide": true,
          "isCarousel": true
        }
      ],
      "cyom": true,
      "closedTime": "2023-11-07T05:31:56Z",
      "showAllOutcomes": true,
      "showMarketImages": true,
      "automaticallyResolved": true,
      "enableNegRisk": true,
      "automaticallyActive": true,
      "eventDate": "<string>",
      "startTime": "2023-11-07T05:31:56Z",
      "eventWeek": 123,
      "seriesSlug": "<string>",
      "score": "<string>",
      "elapsed": "<string>",
      "period": "<string>",
      "live": true,
      "ended": true,
      "finishedTimestamp": "2023-11-07T05:31:56Z",
      "gmpChartMode": "<string>",
      "eventCreators": [
        {
          "id": "<string>",
          "creatorName": "<string>",
          "creatorHandle": "<string>",
          "creatorUrl": "<string>",
          "creatorImage": "<string>",
          "createdAt": "2023-11-07T05:31:56Z",
          "updatedAt": "2023-11-07T05:31:56Z"
        }
      ],
      "tweetCount": 123,
      "chats": [
        {
          "id": "<string>",
          "channelId": "<string>",
          "channelName": "<string>",
          "channelImage": "<string>",
          "live": true,
          "startTime": "2023-11-07T05:31:56Z",
          "endTime": "2023-11-07T05:31:56Z"
        }
      ],
      "featuredOrder": 123,
      "estimateValue": true,
      "cantEstimate": true,
      "estimatedValue": "<string>",
      "templates": [
        {
          "id": "<string>",
          "eventTitle": "<string>",
          "eventSlug": "<string>",
          "eventImage": "<string>",
          "marketTitle": "<string>",
          "description": "<string>",
          "resolutionSource": "<string>",
          "negRisk": true,
          "sortBy": "<string>",
          "showMarketImages": true,
          "seriesSlug": "<string>",
          "outcomes": "<string>"
        }
      ],
      "spreadsMainLine": 123,
      "totalsMainLine": 123,
      "carouselMap": "<string>",
      "pendingDeployment": true,
      "deploying": true,
      "deployingTimestamp": "2023-11-07T05:31:56Z",
      "scheduledDeploymentTimestamp": "2023-11-07T05:31:56Z",
      "gameStatus": "<string>"
    }
  ],
  "categories": [
    {
      "id": "<string>",
      "label": "<string>",
      "parentCategory": "<string>",
      "slug": "<string>",
      "publishedAt": "<string>",
      "createdBy": "<string>",
      "updatedBy": "<string>",
      "createdAt": "2023-11-07T05:31:56Z",
      "updatedAt": "2023-11-07T05:31:56Z"
    }
  ],
  "tags": [
    {
      "id": "<string>",
      "label": "<string>",
      "slug": "<string>",
      "forceShow": true,
      "publishedAt": "<string>",
      "createdBy": 123,
      "updatedBy": 123,
      "createdAt": "2023-11-07T05:31:56Z",
      "updatedAt": "2023-11-07T05:31:56Z",
      "forceHide": true,
      "isCarousel": true
    }
  ],
  "creator": "<string>",
  "ready": true,
  "funded": true,
  "pastSlugs": "<string>",
  "readyTimestamp": "2023-11-07T05:31:56Z",
  "fundedTimestamp": "2023-11-07T05:31:56Z",
  "acceptingOrdersTimestamp": "2023-11-07T05:31:56Z",
  "competitive": 123,
  "rewardsMinSize": 123,
  "rewardsMaxSpread": 123,
  "spread": 123,
  "automaticallyResolved": true,
  "oneDayPriceChange": 123,
  "oneHourPriceChange": 123,
  "oneWeekPriceChange": 123,
  "oneMonthPriceChange": 123,
  "oneYearPriceChange": 123,
  "lastTradePrice": 123,
  "bestBid": 123,
  "bestAsk": 123,
  "automaticallyActive": true,
  "clearBookOnStart": true,
  "chartColor": "<string>",
  "seriesColor": "<string>",
  "showGmpSeries": true,
  "showGmpOutcome": true,
  "manualActivation": true,
  "negRiskOther": true,
  "gameId": "<string>",
  "groupItemRange": "<string>",
  "sportsMarketType": "<string>",
  "line": 123,
  "umaResolutionStatuses": "<string>",
  "pendingDeployment": true,
  "deploying": true,
  "deployingTimestamp": "2023-11-07T05:31:56Z",
  "scheduledDeploymentTimestamp": "2023-11-07T05:31:56Z",
  "rfqEnabled": true,
  "eventStartTime": "2023-11-07T05:31:56Z"
}

List series

curl --request GET \
  --url https://gamma-api.polymarket.com/series

200
[
  {
    "id": "<string>",
    "ticker": "<string>",
    "slug": "<string>",
    "title": "<string>",
    "subtitle": "<string>",
    "seriesType": "<string>",
    "recurrence": "<string>",
    "description": "<string>",
    "image": "<string>",
    "icon": "<string>",
    "layout": "<string>",
    "active": true,
    "closed": true,
    "archived": true,
    "new": true,
    "featured": true,
    "restricted": true,
    "isTemplate": true,
    "templateVariables": true,
    "publishedAt": "<string>",
    "createdBy": "<string>",
    "updatedBy": "<string>",
    "createdAt": "2023-11-07T05:31:56Z",
    "updatedAt": "2023-11-07T05:31:56Z",
    "commentsEnabled": true,
    "competitive": "<string>",
    "volume24hr": 123,
    "volume": 123,
    "liquidity": 123,
    "startDate": "2023-11-07T05:31:56Z",
    "pythTokenID": "<string>",
    "cgAssetName": "<string>",
    "score": 123,
    "events": [
      {
        "id": "<string>",
        "ticker": "<string>",
        "slug": "<string>",
        "title": "<string>",
        "subtitle": "<string>",
        "description": "<string>",
        "resolutionSource": "<string>",
        "startDate": "2023-11-07T05:31:56Z",
        "creationDate": "2023-11-07T05:31:56Z",
        "endDate": "2023-11-07T05:31:56Z",
        "image": "<string>",
        "icon": "<string>",
        "active": true,
        "closed": true,
        "archived": true,
        "new": true,
        "featured": true,
        "restricted": true,
        "liquidity": 123,
        "volume": 123,
        "openInterest": 123,
        "sortBy": "<string>",
        "category": "<string>",
        "subcategory": "<string>",
        "isTemplate": true,
        "templateVariables": "<string>",
        "published_at": "<string>",
        "createdBy": "<string>",
        "updatedBy": "<string>",
        "createdAt": "2023-11-07T05:31:56Z",
        "updatedAt": "2023-11-07T05:31:56Z",
        "commentsEnabled": true,
        "competitive": 123,
        "volume24hr": 123,
        "volume1wk": 123,
        "volume1mo": 123,
        "volume1yr": 123,
        "featuredImage": "<string>",
        "disqusThread": "<string>",
        "parentEvent": "<string>",
        "enableOrderBook": true,
        "liquidityAmm": 123,
        "liquidityClob": 123,
        "negRisk": true,
        "negRiskMarketID": "<string>",
        "negRiskFeeBips": 123,
        "commentCount": 123,
        "imageOptimized": {
          "id": "<string>",
          "imageUrlSource": "<string>",
          "imageUrlOptimized": "<string>",
          "imageSizeKbSource": 123,
          "imageSizeKbOptimized": 123,
          "imageOptimizedComplete": true,
          "imageOptimizedLastUpdated": "<string>",
          "relID": 123,
          "field": "<string>",
          "relname": "<string>"
        },
        "iconOptimized": {
          "id": "<string>",
          "imageUrlSource": "<string>",
          "imageUrlOptimized": "<string>",
          "imageSizeKbSource": 123,
          "imageSizeKbOptimized": 123,
          "imageOptimizedComplete": true,
          "imageOptimizedLastUpdated": "<string>",
          "relID": 123,
          "field": "<string>",
          "relname": "<string>"
        },
        "featuredImageOptimized": {
          "id": "<string>",
          "imageUrlSource": "<string>",
          "imageUrlOptimized": "<string>",
          "imageSizeKbSource": 123,
          "imageSizeKbOptimized": 123,
          "imageOptimizedComplete": true,
          "imageOptimizedLastUpdated": "<string>",
          "relID": 123,
          "field": "<string>",
          "relname": "<string>"
        },
        "subEvents": [
          "<string>"
        ],
        "markets": [
          {
            "id": "<string>",
            "question": "<string>",
            "conditionId": "<string>",
            "slug": "<string>",
            "twitterCardImage": "<string>",
            "resolutionSource": "<string>",
            "endDate": "2023-11-07T05:31:56Z",
            "category": "<string>",
            "ammType": "<string>",
            "liquidity": "<string>",
            "sponsorName": "<string>",
            "sponsorImage": "<string>",
            "startDate": "2023-11-07T05:31:56Z",
            "xAxisValue": "<string>",
            "yAxisValue": "<string>",
            "denominationToken": "<string>",
            "fee": "<string>",
            "image": "<string>",
            "icon": "<string>",
            "lowerBound": "<string>",
            "upperBound": "<string>",
            "description": "<string>",
            "outcomes": "<string>",
            "outcomePrices": "<string>",
            "volume": "<string>",
            "active": true,
            "marketType": "<string>",
            "formatType": "<string>",
            "lowerBoundDate": "<string>",
            "upperBoundDate": "<string>",
            "closed": true,
            "marketMakerAddress": "<string>",
            "createdBy": 123,
            "updatedBy": 123,
            "createdAt": "2023-11-07T05:31:56Z",
            "updatedAt": "2023-11-07T05:31:56Z",
            "closedTime": "<string>",
            "wideFormat": true,
            "new": true,
            "mailchimpTag": "<string>",
            "featured": true,
            "archived": true,
            "resolvedBy": "<string>",
            "restricted": true,
            "marketGroup": 123,
            "groupItemTitle": "<string>",
            "groupItemThreshold": "<string>",
            "questionID": "<string>",
            "umaEndDate": "<string>",
            "enableOrderBook": true,
            "orderPriceMinTickSize": 123,
            "orderMinSize": 123,
            "umaResolutionStatus": "<string>",
            "curationOrder": 123,
            "volumeNum": 123,
            "liquidityNum": 123,
            "endDateIso": "<string>",
            "startDateIso": "<string>",
            "umaEndDateIso": "<string>",
            "hasReviewedDates": true,
            "readyForCron": true,
            "commentsEnabled": true,
            "volume24hr": 123,
            "volume1wk": 123,
            "volume1mo": 123,
            "volume1yr": 123,
            "gameStartTime": "<string>",
            "secondsDelay": 123,
            "clobTokenIds": "<string>",
            "disqusThread": "<string>",
            "shortOutcomes": "<string>",
            "teamAID": "<string>",
            "teamBID": "<string>",
            "umaBond": "<string>",
            "umaReward": "<string>",
            "fpmmLive": true,
            "volume24hrAmm": 123,
            "volume1wkAmm": 123,
            "volume1moAmm": 123,
            "volume1yrAmm": 123,
            "volume24hrClob": 123,
            "volume1wkClob": 123,
            "volume1moClob": 123,
            "volume1yrClob": 123,
            "volumeAmm": 123,
            "volumeClob": 123,
            "liquidityAmm": 123,
            "liquidityClob": 123,
            "makerBaseFee": 123,
            "takerBaseFee": 123,
            "customLiveness": 123,
            "acceptingOrders": true,
            "notificationsEnabled": true,
            "score": 123,
            "imageOptimized": {
              "id": "<string>",
              "imageUrlSource": "<string>",
              "imageUrlOptimized": "<string>",
              "imageSizeKbSource": 123,
              "imageSizeKbOptimized": 123,
              "imageOptimizedComplete": true,
              "imageOptimizedLastUpdated": "<string>",
              "relID": 123,
              "field": "<string>",
              "relname": "<string>"
            },
            "iconOptimized": {
              "id": "<string>",
              "imageUrlSource": "<string>",
              "imageUrlOptimized": "<string>",
              "imageSizeKbSource": 123,
              "imageSizeKbOptimized": 123,
              "imageOptimizedComplete": true,
              "imageOptimizedLastUpdated": "<string>",
              "relID": 123,
              "field": "<string>",
              "relname": "<string>"
            },
            "events": "<array>",
            "categories": [
              {
                "id": "<string>",
                "label": "<string>",
                "parentCategory": "<string>",
                "slug": "<string>",
                "publishedAt": "<string>",
                "createdBy": "<string>",
                "updatedBy": "<string>",
                "createdAt": "2023-11-07T05:31:56Z",
                "updatedAt": "2023-11-07T05:31:56Z"
              }
            ],
            "tags": [
              {
                "id": "<string>",
                "label": "<string>",
                "slug": "<string>",
                "forceShow": true,
                "publishedAt": "<string>",
                "createdBy": 123,
                "updatedBy": 123,
                "createdAt": "2023-11-07T05:31:56Z",
                "updatedAt": "2023-11-07T05:31:56Z",
                "forceHide": true,
                "isCarousel": true
              }
            ],
            "creator": "<string>",
            "ready": true,
            "funded": true,
            "pastSlugs": "<string>",
            "readyTimestamp": "2023-11-07T05:31:56Z",
            "fundedTimestamp": "2023-11-07T05:31:56Z",
            "acceptingOrdersTimestamp": "2023-11-07T05:31:56Z",
            "competitive": 123,
            "rewardsMinSize": 123,
            "rewardsMaxSpread": 123,
            "spread": 123,
            "automaticallyResolved": true,
            "oneDayPriceChange": 123,
            "oneHourPriceChange": 123,
            "oneWeekPriceChange": 123,
            "oneMonthPriceChange": 123,
            "oneYearPriceChange": 123,
            "lastTradePrice": 123,
            "bestBid": 123,
            "bestAsk": 123,
            "automaticallyActive": true,
            "clearBookOnStart": true,
            "chartColor": "<string>",
            "seriesColor": "<string>",
            "showGmpSeries": true,
            "showGmpOutcome": true,
            "manualActivation": true,
            "negRiskOther": true,
            "gameId": "<string>",
            "groupItemRange": "<string>",
            "sportsMarketType": "<string>",
            "line": 123,
            "umaResolutionStatuses": "<string>",
            "pendingDeployment": true,
            "deploying": true,
            "deployingTimestamp": "2023-11-07T05:31:56Z",
            "scheduledDeploymentTimestamp": "2023-11-07T05:31:56Z",
            "rfqEnabled": true,
            "eventStartTime": "2023-11-07T05:31:56Z"
          }
        ],
        "series": "<array>",
        "categories": [
          {
            "id": "<string>",
            "label": "<string>",
            "parentCategory": "<string>",
            "slug": "<string>",
            "publishedAt": "<string>",
            "createdBy": "<string>",
            "updatedBy": "<string>",
            "createdAt": "2023-11-07T05:31:56Z",
            "updatedAt": "2023-11-07T05:31:56Z"
          }
        ],
        "collections": [
          {
            "id": "<string>",
            "ticker": "<string>",
            "slug": "<string>",
            "title": "<string>",
            "subtitle": "<string>",
            "collectionType": "<string>",
            "description": "<string>",
            "tags": "<string>",
            "image": "<string>",
            "icon": "<string>",
            "headerImage": "<string>",
            "layout": "<string>",
            "active": true,
            "closed": true,
            "archived": true,
            "new": true,
            "featured": true,
            "restricted": true,
            "isTemplate": true,
            "templateVariables": "<string>",
            "publishedAt": "<string>",
            "createdBy": "<string>",
            "updatedBy": "<string>",
            "createdAt": "2023-11-07T05:31:56Z",
            "updatedAt": "2023-11-07T05:31:56Z",
            "commentsEnabled": true,
            "imageOptimized": {
              "id": "<string>",
              "imageUrlSource": "<string>",
              "imageUrlOptimized": "<string>",
              "imageSizeKbSource": 123,
              "imageSizeKbOptimized": 123,
              "imageOptimizedComplete": true,
              "imageOptimizedLastUpdated": "<string>",
              "relID": 123,
              "field": "<string>",
              "relname": "<string>"
            },
            "iconOptimized": {
              "id": "<string>",
              "imageUrlSource": "<string>",
              "imageUrlOptimized": "<string>",
              "imageSizeKbSource": 123,
              "imageSizeKbOptimized": 123,
              "imageOptimizedComplete": true,
              "imageOptimizedLastUpdated": "<string>",
              "relID": 123,
              "field": "<string>",
              "relname": "<string>"
            },
            "headerImageOptimized": {
              "id": "<string>",
              "imageUrlSource": "<string>",
              "imageUrlOptimized": "<string>",
              "imageSizeKbSource": 123,
              "imageSizeKbOptimized": 123,
              "imageOptimizedComplete": true,
              "imageOptimizedLastUpdated": "<string>",
              "relID": 123,
              "field": "<string>",
              "relname": "<string>"
            }
          }
        ],
        "tags": [
          {
            "id": "<string>",
            "label": "<string>",
            "slug": "<string>",
            "forceShow": true,
            "publishedAt": "<string>",
            "createdBy": 123,
            "updatedBy": 123,
            "createdAt": "2023-11-07T05:31:56Z",
            "updatedAt": "2023-11-07T05:31:56Z",
            "forceHide": true,
            "isCarousel": true
          }
        ],
        "cyom": true,
        "closedTime": "2023-11-07T05:31:56Z",
        "showAllOutcomes": true,
        "showMarketImages": true,
        "automaticallyResolved": true,
        "enableNegRisk": true,
        "automaticallyActive": true,
        "eventDate": "<string>",
        "startTime": "2023-11-07T05:31:56Z",
        "eventWeek": 123,
        "seriesSlug": "<string>",
        "score": "<string>",
        "elapsed": "<string>",
        "period": "<string>",
        "live": true,
        "ended": true,
        "finishedTimestamp": "2023-11-07T05:31:56Z",
        "gmpChartMode": "<string>",
        "eventCreators": [
          {
            "id": "<string>",
            "creatorName": "<string>",
            "creatorHandle": "<string>",
            "creatorUrl": "<string>",
            "creatorImage": "<string>",
            "createdAt": "2023-11-07T05:31:56Z",
            "updatedAt": "2023-11-07T05:31:56Z"
          }
        ],
        "tweetCount": 123,
        "chats": [
          {
            "id": "<string>",
            "channelId": "<string>",
            "channelName": "<string>",
            "channelImage": "<string>",
            "live": true,
            "startTime": "2023-11-07T05:31:56Z",
            "endTime": "2023-11-07T05:31:56Z"
          }
        ],
        "featuredOrder": 123,
        "estimateValue": true,
        "cantEstimate": true,
        "estimatedValue": "<string>",
        "templates": [
          {
            "id": "<string>",
            "eventTitle": "<string>",
            "eventSlug": "<string>",
            "eventImage": "<string>",
            "marketTitle": "<string>",
            "description": "<string>",
            "resolutionSource": "<string>",
            "negRisk": true,
            "sortBy": "<string>",
            "showMarketImages": true,
            "seriesSlug": "<string>",
            "outcomes": "<string>"
          }
        ],
        "spreadsMainLine": 123,
        "totalsMainLine": 123,
        "carouselMap": "<string>",
        "pendingDeployment": true,
        "deploying": true,
        "deployingTimestamp": "2023-11-07T05:31:56Z",
        "scheduledDeploymentTimestamp": "2023-11-07T05:31:56Z",
        "gameStatus": "<string>"
      }
    ],
    "collections": [
      {
        "id": "<string>",
        "ticker": "<string>",
        "slug": "<string>",
        "title": "<string>",
        "subtitle": "<string>",
        "collectionType": "<string>",
        "description": "<string>",
        "tags": "<string>",
        "image": "<string>",
        "icon": "<string>",
        "headerImage": "<string>",
        "layout": "<string>",
        "active": true,
        "closed": true,
        "archived": true,
        "new": true,
        "featured": true,
        "restricted": true,
        "isTemplate": true,
        "templateVariables": "<string>",
        "publishedAt": "<string>",
        "createdBy": "<string>",
        "updatedBy": "<string>",
        "createdAt": "2023-11-07T05:31:56Z",
        "updatedAt": "2023-11-07T05:31:56Z",
        "commentsEnabled": true,
        "imageOptimized": {
          "id": "<string>",
          "imageUrlSource": "<string>",
          "imageUrlOptimized": "<string>",
          "imageSizeKbSource": 123,
          "imageSizeKbOptimized": 123,
          "imageOptimizedComplete": true,
          "imageOptimizedLastUpdated": "<string>",
          "relID": 123,
          "field": "<string>",
          "relname": "<string>"
        },
        "iconOptimized": {
          "id": "<string>",
          "imageUrlSource": "<string>",
          "imageUrlOptimized": "<string>",
          "imageSizeKbSource": 123,
          "imageSizeKbOptimized": 123,
          "imageOptimizedComplete": true,
          "imageOptimizedLastUpdated": "<string>",
          "relID": 123,
          "field": "<string>",
          "relname": "<string>"
        },
        "headerImageOptimized": {
          "id": "<string>",
          "imageUrlSource": "<string>",
          "imageUrlOptimized": "<string>",
          "imageSizeKbSource": 123,
          "imageSizeKbOptimized": 123,
          "imageOptimizedComplete": true,
          "imageOptimizedLastUpdated": "<string>",
          "relID": 123,
          "field": "<string>",
          "relname": "<string>"
        }
      }
    ],
    "categories": [
      {
        "id": "<string>",
        "label": "<string>",
        "parentCategory": "<string>",
        "slug": "<string>",
        "publishedAt": "<string>",
        "createdBy": "<string>",
        "updatedBy": "<string>",
        "createdAt": "2023-11-07T05:31:56Z",
        "updatedAt": "2023-11-07T05:31:56Z"
      }
    ],
    "tags": [
      {
        "id": "<string>",
        "label": "<string>",
        "slug": "<string>",
        "forceShow": true,
        "publishedAt": "<string>",
        "createdBy": 123,
        "updatedBy": 123,
        "createdAt": "2023-11-07T05:31:56Z",
        "updatedAt": "2023-11-07T05:31:56Z",
        "forceHide": true,
        "isCarousel": true
      }
    ],
    "commentCount": 123,
    "chats": [
      {
        "id": "<string>",
        "channelId": "<string>",
        "channelName": "<string>",
        "channelImage": "<string>",
        "live": true,
        "startTime": "2023-11-07T05:31:56Z",
        "endTime": "2023-11-07T05:31:56Z"
      }
    ]
  }
]

Get series by id

curl --request GET \
  --url https://gamma-api.polymarket.com/series/{id}

200

404
{
  "id": "<string>",
  "ticker": "<string>",
  "slug": "<string>",
  "title": "<string>",
  "subtitle": "<string>",
  "seriesType": "<string>",
  "recurrence": "<string>",
  "description": "<string>",
  "image": "<string>",
  "icon": "<string>",
  "layout": "<string>",
  "active": true,
  "closed": true,
  "archived": true,
  "new": true,
  "featured": true,
  "restricted": true,
  "isTemplate": true,
  "templateVariables": true,
  "publishedAt": "<string>",
  "createdBy": "<string>",
  "updatedBy": "<string>",
  "createdAt": "2023-11-07T05:31:56Z",
  "updatedAt": "2023-11-07T05:31:56Z",
  "commentsEnabled": true,
  "competitive": "<string>",
  "volume24hr": 123,
  "volume": 123,
  "liquidity": 123,
  "startDate": "2023-11-07T05:31:56Z",
  "pythTokenID": "<string>",
  "cgAssetName": "<string>",
  "score": 123,
  "events": [
    {
      "id": "<string>",
      "ticker": "<string>",
      "slug": "<string>",
      "title": "<string>",
      "subtitle": "<string>",
      "description": "<string>",
      "resolutionSource": "<string>",
      "startDate": "2023-11-07T05:31:56Z",
      "creationDate": "2023-11-07T05:31:56Z",
      "endDate": "2023-11-07T05:31:56Z",
      "image": "<string>",
      "icon": "<string>",
      "active": true,
      "closed": true,
      "archived": true,
      "new": true,
      "featured": true,
      "restricted": true,
      "liquidity": 123,
      "volume": 123,
      "openInterest": 123,
      "sortBy": "<string>",
      "category": "<string>",
      "subcategory": "<string>",
      "isTemplate": true,
      "templateVariables": "<string>",
      "published_at": "<string>",
      "createdBy": "<string>",
      "updatedBy": "<string>",
      "createdAt": "2023-11-07T05:31:56Z",
      "updatedAt": "2023-11-07T05:31:56Z",
      "commentsEnabled": true,
      "competitive": 123,
      "volume24hr": 123,
      "volume1wk": 123,
      "volume1mo": 123,
      "volume1yr": 123,
      "featuredImage": "<string>",
      "disqusThread": "<string>",
      "parentEvent": "<string>",
      "enableOrderBook": true,
      "liquidityAmm": 123,
      "liquidityClob": 123,
      "negRisk": true,
      "negRiskMarketID": "<string>",
      "negRiskFeeBips": 123,
      "commentCount": 123,
      "imageOptimized": {
        "id": "<string>",
        "imageUrlSource": "<string>",
        "imageUrlOptimized": "<string>",
        "imageSizeKbSource": 123,
        "imageSizeKbOptimized": 123,
        "imageOptimizedComplete": true,
        "imageOptimizedLastUpdated": "<string>",
        "relID": 123,
        "field": "<string>",
        "relname": "<string>"
      },
      "iconOptimized": {
        "id": "<string>",
        "imageUrlSource": "<string>",
        "imageUrlOptimized": "<string>",
        "imageSizeKbSource": 123,
        "imageSizeKbOptimized": 123,
        "imageOptimizedComplete": true,
        "imageOptimizedLastUpdated": "<string>",
        "relID": 123,
        "field": "<string>",
        "relname": "<string>"
      },
      "featuredImageOptimized": {
        "id": "<string>",
        "imageUrlSource": "<string>",
        "imageUrlOptimized": "<string>",
        "imageSizeKbSource": 123,
        "imageSizeKbOptimized": 123,
        "imageOptimizedComplete": true,
        "imageOptimizedLastUpdated": "<string>",
        "relID": 123,
        "field": "<string>",
        "relname": "<string>"
      },
      "subEvents": [
        "<string>"
      ],
      "markets": [
        {
          "id": "<string>",
          "question": "<string>",
          "conditionId": "<string>",
          "slug": "<string>",
          "twitterCardImage": "<string>",
          "resolutionSource": "<string>",
          "endDate": "2023-11-07T05:31:56Z",
          "category": "<string>",
          "ammType": "<string>",
          "liquidity": "<string>",
          "sponsorName": "<string>",
          "sponsorImage": "<string>",
          "startDate": "2023-11-07T05:31:56Z",
          "xAxisValue": "<string>",
          "yAxisValue": "<string>",
          "denominationToken": "<string>",
          "fee": "<string>",
          "image": "<string>",
          "icon": "<string>",
          "lowerBound": "<string>",
          "upperBound": "<string>",
          "description": "<string>",
          "outcomes": "<string>",
          "outcomePrices": "<string>",
          "volume": "<string>",
          "active": true,
          "marketType": "<string>",
          "formatType": "<string>",
          "lowerBoundDate": "<string>",
          "upperBoundDate": "<string>",
          "closed": true,
          "marketMakerAddress": "<string>",
          "createdBy": 123,
          "updatedBy": 123,
          "createdAt": "2023-11-07T05:31:56Z",
          "updatedAt": "2023-11-07T05:31:56Z",
          "closedTime": "<string>",
          "wideFormat": true,
          "new": true,
          "mailchimpTag": "<string>",
          "featured": true,
          "archived": true,
          "resolvedBy": "<string>",
          "restricted": true,
          "marketGroup": 123,
          "groupItemTitle": "<string>",
          "groupItemThreshold": "<string>",
          "questionID": "<string>",
          "umaEndDate": "<string>",
          "enableOrderBook": true,
          "orderPriceMinTickSize": 123,
          "orderMinSize": 123,
          "umaResolutionStatus": "<string>",
          "curationOrder": 123,
          "volumeNum": 123,
          "liquidityNum": 123,
          "endDateIso": "<string>",
          "startDateIso": "<string>",
          "umaEndDateIso": "<string>",
          "hasReviewedDates": true,
          "readyForCron": true,
          "commentsEnabled": true,
          "volume24hr": 123,
          "volume1wk": 123,
          "volume1mo": 123,
          "volume1yr": 123,
          "gameStartTime": "<string>",
          "secondsDelay": 123,
          "clobTokenIds": "<string>",
          "disqusThread": "<string>",
          "shortOutcomes": "<string>",
          "teamAID": "<string>",
          "teamBID": "<string>",
          "umaBond": "<string>",
          "umaReward": "<string>",
          "fpmmLive": true,
          "volume24hrAmm": 123,
          "volume1wkAmm": 123,
          "volume1moAmm": 123,
          "volume1yrAmm": 123,
          "volume24hrClob": 123,
          "volume1wkClob": 123,
          "volume1moClob": 123,
          "volume1yrClob": 123,
          "volumeAmm": 123,
          "volumeClob": 123,
          "liquidityAmm": 123,
          "liquidityClob": 123,
          "makerBaseFee": 123,
          "takerBaseFee": 123,
          "customLiveness": 123,
          "acceptingOrders": true,
          "notificationsEnabled": true,
          "score": 123,
          "imageOptimized": {
            "id": "<string>",
            "imageUrlSource": "<string>",
            "imageUrlOptimized": "<string>",
            "imageSizeKbSource": 123,
            "imageSizeKbOptimized": 123,
            "imageOptimizedComplete": true,
            "imageOptimizedLastUpdated": "<string>",
            "relID": 123,
            "field": "<string>",
            "relname": "<string>"
          },
          "iconOptimized": {
            "id": "<string>",
            "imageUrlSource": "<string>",
            "imageUrlOptimized": "<string>",
            "imageSizeKbSource": 123,
            "imageSizeKbOptimized": 123,
            "imageOptimizedComplete": true,
            "imageOptimizedLastUpdated": "<string>",
            "relID": 123,
            "field": "<string>",
            "relname": "<string>"
          },
          "events": "<array>",
          "categories": [
            {
              "id": "<string>",
              "label": "<string>",
              "parentCategory": "<string>",
              "slug": "<string>",
              "publishedAt": "<string>",
              "createdBy": "<string>",
              "updatedBy": "<string>",
              "createdAt": "2023-11-07T05:31:56Z",
              "updatedAt": "2023-11-07T05:31:56Z"
            }
          ],
          "tags": [
            {
              "id": "<string>",
              "label": "<string>",
              "slug": "<string>",
              "forceShow": true,
              "publishedAt": "<string>",
              "createdBy": 123,
              "updatedBy": 123,
              "createdAt": "2023-11-07T05:31:56Z",
              "updatedAt": "2023-11-07T05:31:56Z",
              "forceHide": true,
              "isCarousel": true
            }
          ],
          "creator": "<string>",
          "ready": true,
          "funded": true,
          "pastSlugs": "<string>",
          "readyTimestamp": "2023-11-07T05:31:56Z",
          "fundedTimestamp": "2023-11-07T05:31:56Z",
          "acceptingOrdersTimestamp": "2023-11-07T05:31:56Z",
          "competitive": 123,
          "rewardsMinSize": 123,
          "rewardsMaxSpread": 123,
          "spread": 123,
          "automaticallyResolved": true,
          "oneDayPriceChange": 123,
          "oneHourPriceChange": 123,
          "oneWeekPriceChange": 123,
          "oneMonthPriceChange": 123,
          "oneYearPriceChange": 123,
          "lastTradePrice": 123,
          "bestBid": 123,
          "bestAsk": 123,
          "automaticallyActive": true,
          "clearBookOnStart": true,
          "chartColor": "<string>",
          "seriesColor": "<string>",
          "showGmpSeries": true,
          "showGmpOutcome": true,
          "manualActivation": true,
          "negRiskOther": true,
          "gameId": "<string>",
          "groupItemRange": "<string>",
          "sportsMarketType": "<string>",
          "line": 123,
          "umaResolutionStatuses": "<string>",
          "pendingDeployment": true,
          "deploying": true,
          "deployingTimestamp": "2023-11-07T05:31:56Z",
          "scheduledDeploymentTimestamp": "2023-11-07T05:31:56Z",
          "rfqEnabled": true,
          "eventStartTime": "2023-11-07T05:31:56Z"
        }
      ],
      "series": "<array>",
      "categories": [
        {
          "id": "<string>",
          "label": "<string>",
          "parentCategory": "<string>",
          "slug": "<string>",
          "publishedAt": "<string>",
          "createdBy": "<string>",
          "updatedBy": "<string>",
          "createdAt": "2023-11-07T05:31:56Z",
          "updatedAt": "2023-11-07T05:31:56Z"
        }
      ],
      "collections": [
        {
          "id": "<string>",
          "ticker": "<string>",
          "slug": "<string>",
          "title": "<string>",
          "subtitle": "<string>",
          "collectionType": "<string>",
          "description": "<string>",
          "tags": "<string>",
          "image": "<string>",
          "icon": "<string>",
          "headerImage": "<string>",
          "layout": "<string>",
          "active": true,
          "closed": true,
          "archived": true,
          "new": true,
          "featured": true,
          "restricted": true,
          "isTemplate": true,
          "templateVariables": "<string>",
          "publishedAt": "<string>",
          "createdBy": "<string>",
          "updatedBy": "<string>",
          "createdAt": "2023-11-07T05:31:56Z",
          "updatedAt": "2023-11-07T05:31:56Z",
          "commentsEnabled": true,
          "imageOptimized": {
            "id": "<string>",
            "imageUrlSource": "<string>",
            "imageUrlOptimized": "<string>",
            "imageSizeKbSource": 123,
            "imageSizeKbOptimized": 123,
            "imageOptimizedComplete": true,
            "imageOptimizedLastUpdated": "<string>",
            "relID": 123,
            "field": "<string>",
            "relname": "<string>"
          },
          "iconOptimized": {
            "id": "<string>",
            "imageUrlSource": "<string>",
            "imageUrlOptimized": "<string>",
            "imageSizeKbSource": 123,
            "imageSizeKbOptimized": 123,
            "imageOptimizedComplete": true,
            "imageOptimizedLastUpdated": "<string>",
            "relID": 123,
            "field": "<string>",
            "relname": "<string>"
          },
          "headerImageOptimized": {
            "id": "<string>",
            "imageUrlSource": "<string>",
            "imageUrlOptimized": "<string>",
            "imageSizeKbSource": 123,
            "imageSizeKbOptimized": 123,
            "imageOptimizedComplete": true,
            "imageOptimizedLastUpdated": "<string>",
            "relID": 123,
            "field": "<string>",
            "relname": "<string>"
          }
        }
      ],
      "tags": [
        {
          "id": "<string>",
          "label": "<string>",
          "slug": "<string>",
          "forceShow": true,
          "publishedAt": "<string>",
          "createdBy": 123,
          "updatedBy": 123,
          "createdAt": "2023-11-07T05:31:56Z",
          "updatedAt": "2023-11-07T05:31:56Z",
          "forceHide": true,
          "isCarousel": true
        }
      ],
      "cyom": true,
      "closedTime": "2023-11-07T05:31:56Z",
      "showAllOutcomes": true,
      "showMarketImages": true,
      "automaticallyResolved": true,
      "enableNegRisk": true,
      "automaticallyActive": true,
      "eventDate": "<string>",
      "startTime": "2023-11-07T05:31:56Z",
      "eventWeek": 123,
      "seriesSlug": "<string>",
      "score": "<string>",
      "elapsed": "<string>",
      "period": "<string>",
      "live": true,
      "ended": true,
      "finishedTimestamp": "2023-11-07T05:31:56Z",
      "gmpChartMode": "<string>",
      "eventCreators": [
        {
          "id": "<string>",
          "creatorName": "<string>",
          "creatorHandle": "<string>",
          "creatorUrl": "<string>",
          "creatorImage": "<string>",
          "createdAt": "2023-11-07T05:31:56Z",
          "updatedAt": "2023-11-07T05:31:56Z"
        }
      ],
      "tweetCount": 123,
      "chats": [
        {
          "id": "<string>",
          "channelId": "<string>",
          "channelName": "<string>",
          "channelImage": "<string>",
          "live": true,
          "startTime": "2023-11-07T05:31:56Z",
          "endTime": "2023-11-07T05:31:56Z"
        }
      ],
      "featuredOrder": 123,
      "estimateValue": true,
      "cantEstimate": true,
      "estimatedValue": "<string>",
      "templates": [
        {
          "id": "<string>",
          "eventTitle": "<string>",
          "eventSlug": "<string>",
          "eventImage": "<string>",
          "marketTitle": "<string>",
          "description": "<string>",
          "resolutionSource": "<string>",
          "negRisk": true,
          "sortBy": "<string>",
          "showMarketImages": true,
          "seriesSlug": "<string>",
          "outcomes": "<string>"
        }
      ],
      "spreadsMainLine": 123,
      "totalsMainLine": 123,
      "carouselMap": "<string>",
      "pendingDeployment": true,
      "deploying": true,
      "deployingTimestamp": "2023-11-07T05:31:56Z",
      "scheduledDeploymentTimestamp": "2023-11-07T05:31:56Z",
      "gameStatus": "<string>"
    }
  ],
  "collections": [
    {
      "id": "<string>",
      "ticker": "<string>",
      "slug": "<string>",
      "title": "<string>",
      "subtitle": "<string>",
      "collectionType": "<string>",
      "description": "<string>",
      "tags": "<string>",
      "image": "<string>",
      "icon": "<string>",
      "headerImage": "<string>",
      "layout": "<string>",
      "active": true,
      "closed": true,
      "archived": true,
      "new": true,
      "featured": true,
      "restricted": true,
      "isTemplate": true,
      "templateVariables": "<string>",
      "publishedAt": "<string>",
      "createdBy": "<string>",
      "updatedBy": "<string>",
      "createdAt": "2023-11-07T05:31:56Z",
      "updatedAt": "2023-11-07T05:31:56Z",
      "commentsEnabled": true,
      "imageOptimized": {
        "id": "<string>",
        "imageUrlSource": "<string>",
        "imageUrlOptimized": "<string>",
        "imageSizeKbSource": 123,
        "imageSizeKbOptimized": 123,
        "imageOptimizedComplete": true,
        "imageOptimizedLastUpdated": "<string>",
        "relID": 123,
        "field": "<string>",
        "relname": "<string>"
      },
      "iconOptimized": {
        "id": "<string>",
        "imageUrlSource": "<string>",
        "imageUrlOptimized": "<string>",
        "imageSizeKbSource": 123,
        "imageSizeKbOptimized": 123,
        "imageOptimizedComplete": true,
        "imageOptimizedLastUpdated": "<string>",
        "relID": 123,
        "field": "<string>",
        "relname": "<string>"
      },
      "headerImageOptimized": {
        "id": "<string>",
        "imageUrlSource": "<string>",
        "imageUrlOptimized": "<string>",
        "imageSizeKbSource": 123,
        "imageSizeKbOptimized": 123,
        "imageOptimizedComplete": true,
        "imageOptimizedLastUpdated": "<string>",
        "relID": 123,
        "field": "<string>",
        "relname": "<string>"
      }
    }
  ],
  "categories": [
    {
      "id": "<string>",
      "label": "<string>",
      "parentCategory": "<string>",
      "slug": "<string>",
      "publishedAt": "<string>",
      "createdBy": "<string>",
      "updatedBy": "<string>",
      "createdAt": "2023-11-07T05:31:56Z",
      "updatedAt": "2023-11-07T05:31:56Z"
    }
  ],
  "tags": [
    {
      "id": "<string>",
      "label": "<string>",
      "slug": "<string>",
      "forceShow": true,
      "publishedAt": "<string>",
      "createdBy": 123,
      "updatedBy": 123,
      "createdAt": "2023-11-07T05:31:56Z",
      "updatedAt": "2023-11-07T05:31:56Z",
      "forceHide": true,
      "isCarousel": true
    }
  ],
  "commentCount": 123,
  "chats": [
    {
      "id": "<string>",
      "channelId": "<string>",
      "channelName": "<string>",
      "channelImage": "<string>",
      "live": true,
      "startTime": "2023-11-07T05:31:56Z",
      "endTime": "2023-11-07T05:31:56Z"
    }
  ]
}





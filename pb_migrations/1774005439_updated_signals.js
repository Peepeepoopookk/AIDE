/// <reference path="../pb_data/types.d.ts" />
migrate((app) => {
  const collection = app.findCollectionByNameOrId("pbc_1207876327")

  // add field
  collection.fields.addAt(15, new Field({
    "hidden": false,
    "id": "bool2223223449",
    "name": "scored",
    "presentable": false,
    "required": false,
    "system": false,
    "type": "bool"
  }))

  // add field
  collection.fields.addAt(16, new Field({
    "autogeneratePattern": "",
    "hidden": false,
    "id": "text641166343",
    "max": 0,
    "min": 0,
    "name": "skip_reason",
    "pattern": "",
    "presentable": false,
    "primaryKey": false,
    "required": false,
    "system": false,
    "type": "text"
  }))

  // add field
  collection.fields.addAt(17, new Field({
    "hidden": false,
    "id": "json1164694065",
    "maxSize": 0,
    "name": "classification",
    "presentable": false,
    "required": false,
    "system": false,
    "type": "json"
  }))

  // add field
  collection.fields.addAt(18, new Field({
    "hidden": false,
    "id": "json2280354325",
    "maxSize": 0,
    "name": "score_data",
    "presentable": false,
    "required": false,
    "system": false,
    "type": "json"
  }))

  // add field
  collection.fields.addAt(19, new Field({
    "hidden": false,
    "id": "json1395575714",
    "maxSize": 0,
    "name": "summary_data",
    "presentable": false,
    "required": false,
    "system": false,
    "type": "json"
  }))

  // add field
  collection.fields.addAt(20, new Field({
    "hidden": false,
    "id": "json2621486728",
    "maxSize": 0,
    "name": "analysis_data",
    "presentable": false,
    "required": false,
    "system": false,
    "type": "json"
  }))

  return app.save(collection)
}, (app) => {
  const collection = app.findCollectionByNameOrId("pbc_1207876327")

  // remove field
  collection.fields.removeById("bool2223223449")

  // remove field
  collection.fields.removeById("text641166343")

  // remove field
  collection.fields.removeById("json1164694065")

  // remove field
  collection.fields.removeById("json2280354325")

  // remove field
  collection.fields.removeById("json1395575714")

  // remove field
  collection.fields.removeById("json2621486728")

  return app.save(collection)
})

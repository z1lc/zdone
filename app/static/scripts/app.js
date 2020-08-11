function completeItem(service, id, raw_name) {
  updateItem(service, id, raw_name, "complete");
}

function deferItem(service, id, raw_name) {
  updateItem(service, id, raw_name, "defer");
}

function updateItem(service, id, raw_name, updateAction) {
  if (service === "zdone" || service === "trello") {
    $
      .ajax({
        contentType: "application/json",
        data: JSON.stringify({
          "service": service,
          "id": id,
          "raw_name": raw_name,
          "update": updateAction,
        }),
        type: "POST",
        url: "update_task"
      });
  } else {
    alert("Unexpected service '" + service + "'!")
  }
}

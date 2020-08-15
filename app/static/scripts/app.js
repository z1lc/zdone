function completeItem(service, id, raw_name) {
  updateItem(service, id, null, raw_name, "complete");
}

function deferItem(service, id, days, raw_name) {
  updateItem(service, id, days, raw_name, "defer");
}

function updateItem(service, id, days, raw_name, updateAction) {
  if (service === "zdone" || service === "trello") {
    $
      .ajax({
        contentType: "application/json",
        data: JSON.stringify({
          "service": service,
          "id": id,
          "days": days,
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

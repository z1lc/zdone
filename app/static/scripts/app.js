function completeItem(service, id, rawName) {
  updateItem(service, id, null, rawName, "complete", null);
}

function deferItem(service, id, days, rawName) {
  updateItem(service, id, days, rawName, "defer", null);
}

function moveItem(id, toListId) {
  updateItem("trello", id, null, null, "move", toListId);
}

function updateItem(service, id, days, rawName, updateAction, toListId) {
  if (service === "zdone" || service === "trello") {
    $
      .ajax({
        contentType: "application/json",
        data: JSON.stringify({
          "service": service,
          "id": id,
          "days": days,
          "raw_name": rawName,
          "update": updateAction,
          "to_list_id": toListId,
        }),
        type: "POST",
        url: "update_task"
      });
  } else {
    alert(`Unexpected service '${service}'!`)
  }
}

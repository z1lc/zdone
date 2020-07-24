function completeItem(service, id) {
  updateItem(service, id, "complete");
}

function deferItem(service, id) {
  updateItem(service, id, "defer");
}

function updateItem(service, id, updateAction) {
  if (service === "zdone" || service === "trello") {
    $
      .ajax({
        contentType: "application/json",
        data: JSON.stringify({
          "service": service,
          "id": id,
          "update": updateAction,
        }),
        type: "POST",
        url: "update_task"
      });
  } else {
    alert("Unexpected service '" + service + "'!")
  }
}

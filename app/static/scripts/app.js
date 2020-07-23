function completeItem(service, id, subtaskId, durationSeconds = 0) {
  updateItem(service, id, subtaskId, "complete", durationSeconds);
}

function deferItem(service, id, subtaskId, durationSeconds = 0) {
  updateItem(service, id, subtaskId, "defer", durationSeconds);
}

function updateItem(service, id, subtaskId, updateAction, durationSeconds) {
  if (service === "zdone" || service === "trello") {
    $
      .ajax({
        contentType: "application/json",
        data: JSON.stringify({
          "service": service,
          "id": id,
          "subtask_id": subtaskId,
          "update": updateAction,
          "duration_seconds": durationSeconds
        }),
        type: "POST",
        url: "update_task"
      });
  } else {
    alert("Unexpected service '" + service + "'!")
  }
}

function getSelector(service, id, subtask_id, use_class_selector = false) {
  let toReturn = "";
  if (use_class_selector) {
    toReturn += "."
  } else {
    toReturn += "#"
  }
  toReturn += service + "-" + id;
  if (subtask_id !== "") {
    toReturn += "-" + subtask_id
  }
  return toReturn
}

function completeItem(service, id, subtask_id) {
  $(getSelector(service, id, subtask_id)).find(".check").css("color", "green");
  updateItem(service, id, subtask_id, "complete")
}

function deferItem(service, id, subtask_id) {
  $(getSelector(service, id, subtask_id)).find(".defer").css("color", "#111198");
  updateItem(service, id, subtask_id, "defer")
}

function updateItem(service, id, subtask_id, update_action) {
  if (service === "toodledo" || service === "habitica") {
    $
      .ajax({
        contentType: "application/json",
        data: JSON.stringify({
          "service": service,
          "id": id,
          "subtask_id": subtask_id,
          "update": update_action
        }),
        type: "POST",
        url: "update_task"
      })
      .done(function () {
        $(getSelector(service, id, subtask_id)).slideUp();
        $(getSelector(service, id, subtask_id, true)).slideUp();
      });
  } else {
    alert("Unexpected service '" + service + "'!")
  }
}

function setTimeAndReload(new_time) {
  if (new_time !== null && new_time !== '' && !isNaN(new_time)) {
    $
      .ajax({
        contentType: "application/json",
        data: JSON.stringify({
          "maximum_minutes_per_day": new_time
        }),
        type: "POST",
        url: "update_time"
      })
      .done(function () {
        document.location.reload(true);
      });
  }
}

var socket = io();
socket.on('hide task', function (msg) {
  $(getSelector(msg['service'], msg['task_id'], msg['subtask_id'])).slideUp();
  $(getSelector(msg['service'], msg['task_id'], msg['subtask_id'], true)).slideUp();
});
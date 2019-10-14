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

function animateProgressBar(completedMinutes, deferredMinutes) {
  let defaultProps = {duration: 1000, queue: false};
  let $minCompleted = $("#minutes_completed");
  let $minTotal = $("#minutes_total");

  let newMinCompleted = parseInt($minCompleted.text()) + completedMinutes;
  let newMinTotal = parseInt($minTotal.text()) - deferredMinutes;

  $minCompleted
    .prop('number', parseInt($minCompleted.text()))
    .animateNumber({number: newMinCompleted}, defaultProps);
  $minTotal
    .prop('number', parseInt($minTotal.text()))
    .animateNumber({number: newMinTotal}, defaultProps);
  let toAnimateProgressBar = {
    width: ((newMinCompleted / newMinTotal * 100) + '%')
  };

  let toAnimateMinutesCompleted = {};
  if (newMinCompleted >= 30 || newMinCompleted === newMinTotal) {
    toAnimateProgressBar['backgroundColor'] = '#2196F3 !important';
    toAnimateMinutesCompleted['opacity'] = 1.0;
  }
  $("#progress_bar").animate(toAnimateProgressBar, defaultProps);
  $minCompleted.animate(toAnimateMinutesCompleted, defaultProps);
}

function completeItem(service, id, subtask_id, length = 0) {
  $(getSelector(service, id, subtask_id)).find(".check").css("color", "green");
  updateItem(service, id, subtask_id, "complete");
  animateProgressBar(length, 0);
}

function deferItem(service, id, subtask_id, length = 0) {
  $(getSelector(service, id, subtask_id)).find(".defer").css("color", "#111198");
  updateItem(service, id, subtask_id, "defer");
  animateProgressBar(0, length);
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
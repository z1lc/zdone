let animatedIds = new Set();

function getSelector(service, id, subtaskId, useClassSelector = false) {
  let toReturn = "";
  if (useClassSelector) {
    toReturn += "."
  } else {
    toReturn += "#"
  }
  toReturn += service + "-" + id;
  if (subtaskId !== "") {
    toReturn += "-" + subtaskId
  }
  return toReturn
}

function animateProgressBar(id, action, minutes) {
  if (animatedIds.has(id)) {
    return;
  }

  animatedIds.add(id);
  let completedMinutes = 0, deferredMinutes = 0;
  if (action === 'defer') {
    deferredMinutes = minutes;
  } else if (action === 'complete') {
    completedMinutes = minutes;
  }

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

function completeItem(service, id, subtaskId, length = 0) {
  let idSelector = getSelector(service, id, subtaskId);
  $(idSelector).find(".check").css("color", "green");
  updateItem(service, id, subtaskId, "complete");
  animateProgressBar(idSelector, 'complete', length);
}

function deferItem(service, id, subtaskId, length = 0) {
  let idSelector = getSelector(service, id, subtaskId);
  $(idSelector).find(".defer").css("color", "#111198");
  updateItem(service, id, subtaskId, "defer");
  animateProgressBar(idSelector, 'defer', length);
}

function updateItem(service, id, subtaskId, updateAction) {
  if (service === "toodledo" || service === "habitica") {
    $
      .ajax({
        contentType: "application/json",
        data: JSON.stringify({
          "service": service,
          "id": id,
          "subtask_id": subtaskId,
          "update": updateAction
        }),
        type: "POST",
        url: "update_task"
      })
      .done(function () {
        $(getSelector(service, id, subtaskId)).slideUp();
        $(getSelector(service, id, subtaskId, true)).slideUp();
      });
  } else {
    alert("Unexpected service '" + service + "'!")
  }
}

function setTimeAndReload(newTime) {
  if (newTime !== null && newTime !== '' && !isNaN(newTime)) {
    $
      .ajax({
        contentType: "application/json",
        data: JSON.stringify({
          "maximum_minutes_per_day": newTime
        }),
        type: "POST",
        url: "update_time"
      })
      .done(function () {
        document.location.reload(true);
      });
  }
}

function showTrelloList(optionElement) {
  $('#trello_lists').find('div.trello_list').slideUp();
  $('#trello_lists').find('div#trello-' + optionElement.value.replace(/ /g,"")).slideDown();
}


let socket = io();
socket.on($('script[src*=app]').attr('data-api-key'), function (msg) {
  let idSelector = getSelector(msg['service'], msg['task_id'], msg['subtask_id']);
  animateProgressBar(idSelector, msg['update'], msg['length_minutes']);
  $(idSelector).slideUp();
  $(getSelector(msg['service'], msg['task_id'], msg['subtask_id'], true)).slideUp();
});

$(function () {
  $('#trello_lists').find('div#trello-' + $('#trello_lists_select').find(':selected').val()).slideDown();
});
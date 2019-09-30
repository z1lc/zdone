$(function () {
  $("#unsorted, #sorted").sortable({
    placeholder: "ui-state-highlight",
    connectWith: ".connectedSortable"
  }).disableSelection();
  $("#sorted").on("sortupdate", function (event, ui) {
    $.ajax({
      contentType: "application/json",
      data: JSON.stringify({
        "{{ type }}": $("#sorted span.taskTitle").toArray()
          .map(e => $(e).text())
          .join("|||")
      }),
      type: "POST",
      url: "set_{{ type }}"
    });
  });
});
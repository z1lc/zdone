$(function () {
  let dialog,
    form,
    title = $("#title"),
    due_date = $("#due_date"),
    length_minutes = $("#length_minutes"),
    allFields = $([]).add(title).add(due_date).add(length_minutes),
    tips = $(".validateTips");

  function updateTips(t) {
    tips
      .text(t)
      .addClass("ui-state-highlight");
    setTimeout(function () {
      tips.removeClass("ui-state-highlight", 1500);
    }, 500);
  }

  function checkLength(o, n, min, max) {
    if (o.val().length > max || o.val().length < min) {
      o.addClass("ui-state-error");
      updateTips("Length of " + n + " must be between " +
        min + " and " + max + ".");
      return false;
    } else {
      return true;
    }
  }

  function checkRegexp(o, regexp, n) {
    if (!(regexp.test(o.val()))) {
      o.addClass("ui-state-error");
      updateTips(n);
      return false;
    } else {
      return true;
    }
  }

  function addUser() {
    let valid = true;
    allFields.removeClass("ui-state-error");

    valid = valid && checkLength(title, "task title", 1, 100);

    valid = valid && checkRegexp(title, /^[a-z]([0-9a-z\-_\s])*$/i, "Title may consist of a-z, 0-9, underscores, spaces and must begin with a letter.");

    if (valid) {
      $
        .ajax({
          contentType: "application/json",
          data: JSON.stringify({
            "name": title.val(),
            "due_date": due_date.val(),
            "length_minutes": length_minutes.val()
          }),
          type: "POST",
          url: "add_task"
        })
        .done(function () {
          document.location.reload(true);
        });
      dialog.dialog("close");
    }
    return valid;
  }

  dialog = $("#dialog-form").dialog({
    autoOpen: false,
    resizable: false,
    width: 450,
    modal: true,
    buttons: {
      "Create task": addUser
    },
    close: function () {
      form[0].reset();
      allFields.removeClass("ui-state-error");
    }
  });

  form = dialog.find("form").on("submit", function (event) {
    event.preventDefault();
    addUser();
  });

  $("#create-task").button().on("click", function () {
    dialog.dialog("open");
  });
});
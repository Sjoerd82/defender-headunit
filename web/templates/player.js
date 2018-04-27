function receive_hello(data){
    $("#mytarget").html(data.result)
}

function send_hello(jqevent) {
    $.getJSON("/hello", {}, receive_hello)
}

function player_next(jqevent) {
    $.getJSON("/hu/api/v1.0/player/next")
}

function player_random(jqevent) {
	alert("hi!")
	alert(this.className)
}

$( document ).ready(function() {
  $( "#source-next" ).click($.getJSON("/hu/api/v1.0/source/next"));
  $( "#source-prev" ).click($.getJSON("/hu/api/v1.0/source/prev"));
  $( "#player-next" ).click(player_next);
  $( "#player-prev" ).click($.getJSON("/hu/api/v1.0/player/prev"));
  $( "#player-mode-play"  ).click($.getJSON("/hu/api/v1.0/player/mode/play"));
  $( "#player-mode-pause" ).click($.getJSON("/hu/api/v1.0/player/mode/pause"));
  $( "#player-mode-stop" ).click($.getJSON("/hu/api/v1.0/player/mode/stop"));
  $( "#player-random" ).click(player_random);
  $( "#player-update" ).click($.getJSON("/hu/api/v1.0/player/update"));
});

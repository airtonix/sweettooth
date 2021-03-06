"use strict";

define(['jquery'], function($) {

    function createFileView(data) {
        var rawLines = data.raw.split("\n");
        var count = rawLines.length;
        if (rawLines[count-1] == "")
            count --;
        if (rawLines[0] == "")
            count --;

        var lines = "";
        lines += "<td class=\"linenumbers\"><pre>";
        for (var i = 1; i < (count + 1); i ++) {
            lines += "<span rel=\"L" + i + "\">" + i + "</span>\n";
        }
        lines += "</pre></td>";

        var file = "<td width=\"100%\"><div class=\"file\">" + data.html + "</div></td>";

        return $("<table><tr>" + lines + file + "</tr></div>");
    }

    $.fn.reviewify = function(fileurl) {
        var $elem = $(this);
        var $fileList = $('<ul>', {'class': 'filelist'}).appendTo($elem);

        // Hide the file list until we're done grabbing all the elements.
        $fileList.hide();

        var $fileDisplay = $('<div>', {'class': 'filedisplay'}).appendTo($elem);
        $fileDisplay.css('position', 'relative');

        var $currentFile = null;

        var req = $.ajax({
            type: 'GET',
            dataType: 'json',
            url: fileurl
        });

        req.done(function(data) {
            $.each(data, function() {
                var data = this;
                var $selector = $('<a>', {'class': 'fileselector'}).text(data.filename);

                $selector.click(function() {
                    if ($selector.hasClass('selected'))
                        return;

                    var $file = createFileView(data).hide().appendTo($fileDisplay);
                    $fileList.find('li a.fileselector').removeClass('selected');
                    $selector.addClass('selected');

                    $file.css('position', 'relative');

                    if ($currentFile != null) {
                        $currentFile.css({'position': 'absolute',
                                          'top': '0'});
                        $currentFile.fadeOut();
                        $file.fadeIn();
                    } else {
                        $file.show();
                    }

                    $currentFile = $file;
                });

                $('<li>').append($selector).appendTo($fileList);
            });

            $fileList.show();

            // Select the first item.
            $fileList.find('li a.fileselector').first().click();
        });
    };
});

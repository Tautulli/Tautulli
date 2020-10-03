/**
 * Plugin: "disable_options" (selectize.js)
 * Copyright (c) 2013 Mondo Robot & contributors
 *
 * Licensed under the Apache License, Version 2.0 (the "License"); you may not use this
 * file except in compliance with the License. You may obtain a copy of the License at:
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software distributed under
 * the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
 * ANY KIND, either express or implied. See the License for the specific language
 * governing permissions and limitations under the License.
 *
 * @authors Jake Myers <jmyers0022@gmail.com>, Vaughn Draughon <vaughn@rocksolidwebdesign.com>
 */

 Selectize.define('disable_options', function(options) {
  var self = this;

  options = $.extend({
	'disableField': '',
    'disableOptions': []
  }, options);

  self.refreshOptions = (function() {
    var original = self.refreshOptions;

    return function() {
      original.apply(this, arguments);

      $.each(options.disableOptions, function(index, option) {
        self.$dropdown_content.find('[data-' + options.disableField + '="' + String(option) + '"]').addClass('option-disabled');
      });
    };
  })();

  self.onOptionSelect = (function() {
    var original = self.onOptionSelect;

    return function(e) {
      var value, $target, $option;

      if (e.preventDefault) {
        e.preventDefault();
        e.stopPropagation();
      }

      $target = $(e.currentTarget);

      if ($target.hasClass('option-disabled')) {
        return;
      }
      return original.apply(this, arguments);
    };
  })();

  self.disabledOptions = function() {
    return options.disableOptions;
  }

  self.setDisabledOptions = function( values ) {
    options.disableOptions = values
  }

  self.disableOptions = function( values ) {
    if ( ! ( values instanceof Array ) ) {
      values = [ values ]
    }
    values.forEach( function( val ) {
      if ( options.disableOptions.indexOf( val ) == -1 ) {
        options.disableOptions.push( val )
      }
    } );
  }

  self.enableOptions = function( values ) {
    if ( ! ( values instanceof Array ) ) {
      values = [ values ]
    }
    values.forEach( function( val ) {
      var remove = options.disableOptions.indexOf( val );
      if ( remove + 1 ) {
        options.disableOptions.splice( remove, 1 );
      }
    } );
  }
});
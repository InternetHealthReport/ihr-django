$('.ui.search')
  .search({
    type          : 'category',
    minCharacters : 3,
    apiSettings   : {
      onResponse: function(apiResponse) {
        var
          response = {
            results : {}
          }
        ;
        // translate API response to work with search
        $.each(apiResponse.results, function(index, item) {
          var
            asn   = item.number,
            category = 'AS',
            maxResults = 8
          ;
          if(asn<0){
            category = 'IX';
            asn = -asn;
          }
          if(index >= maxResults) {
            return false;
          }
          // create new category
          if(response.results[category] === undefined) {
            response.results[category] = {
              name    : category,
              results : []
            };
          }
          // add result to category
          response.results[category].results.push({
            title       : item.name,
            description : category+asn,
            url         : '/ihr/'+item.number+'/asn/'
          });
        });
        return response;
      },
      url: '/ihr/api/network/?search={query}&ordering=number',
    }
  })
;

    

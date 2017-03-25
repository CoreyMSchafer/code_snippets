
function html_tag(tag){
  function wrap_text(msg){
    console.log('<' + tag +'>' + msg + '</' + tag + '>')
  }
  return wrap_text
}

print_h1 = html_tag('h1')

print_h1('Test Headline!')
print_h1('Another Headline!')


print_p = html_tag('p')
print_p('Test Paragraph!')
function html_tag(tag) {
  function print_tag(text) {
    return '<'+tag+'>'+text+'</'+tag+'>'
  };
  return print_tag
};

h1_tag = html_tag('h1')

console.log(h1_tag('This is a Headline!'))
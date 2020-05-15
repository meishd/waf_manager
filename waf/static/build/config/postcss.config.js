'use strict'

module.exports = {
  map: ctx.file.dirname.includes('examples') ? false : {
    inline: false,
    annotation: true,
    sourcesContent: true
  },
  plugins: {
    autoprefixer: {
      cascade: false
    }
  }
}
export const TrayPlugin = async ({ $ }) => {
  let prevcolor = ''
  let lastClearedMsgId = ''
  const set = async (color, type) => {
    prevcolor = color
    // console.log(`tray-light.exe ${color} ${type}`)
    // $`tray-light.exe ${color}`.quiet().nothrow()
    // $.verbose = true
    await $`tray-light.exe ${color}`.quiet().nothrow()
    // await $`tray-light.exe red`
  }
  const clear = async (type) => {

    // console.log('enter clear')
    if (!!!prevcolor ) return
    // console.log(`tray-light.exe -${prevcolor} ${type}`)
    // $.verbose = true
    await $`tray-light.exe -${prevcolor}`.quiet().nothrow()
    // await $`/tmp/lc.sh ${prevcolor}`

    prevcolor = ''
  } 

  return {
    event: async ({ event }) => {
      const p = event.properties ?? {}

      switch (event.type) {
        case "session.idle":       await set("green", event.type);  break
        case "session.error":      await set("red", event.type);    break

        case "permission.asked":   await set("yellow", event.type); break
        case "permission.replied": await clear(event.type);   break

        case "message.updated": {

          const info = p.info
          if (!info) break
          if (info.role === "user") {
            // console.log('user message')
            if (info.id === lastClearedMsgId) break
            lastClearedMsgId = info.id
            await clear(event.type);
          }
          break
        }
      }
    },
  }
}

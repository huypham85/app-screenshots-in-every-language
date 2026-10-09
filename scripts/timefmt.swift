// timefmt.swift — how iOS shows times and dates in each locale (Foundation, not guesses).
//
//   swift scripts/timefmt.swift <HH:mm> <yyyy-MM-dd> <locale> [<locale> ...]
//   swift scripts/timefmt.swift 20:00 2026-08-12 en de ko ar hi
//
// Prints per locale: short time, medium date, weekday+day+month, abbreviated month+year,
// and the number 6000 / 1234.5 with that locale's separators (grouping is localized, as on iOS).
import Foundation

let args = Array(CommandLine.arguments.dropFirst())
guard args.count >= 3 else {
    print("usage: timefmt.swift HH:mm yyyy-MM-dd locale [locale ...]")
    exit(1)
}
let hm = args[0].split(separator: ":").compactMap { Int($0) }
let ymd = args[1].split(separator: "-").compactMap { Int($0) }
var parts = DateComponents()
parts.year = ymd[0]; parts.month = ymd[1]; parts.day = ymd[2]
parts.hour = hm[0]; parts.minute = hm[1]
let date = Calendar(identifier: .gregorian).date(from: parts)!

for id in args.dropFirst(2) {
    let locale = Locale(identifier: id)
    let time = DateFormatter(); time.locale = locale; time.timeStyle = .short; time.dateStyle = .none
    let day = DateFormatter(); day.locale = locale; day.timeStyle = .none; day.dateStyle = .medium
    let month = DateFormatter(); month.locale = locale; month.setLocalizedDateFormatFromTemplate("MMMy")
    let weekday = DateFormatter(); weekday.locale = locale; weekday.setLocalizedDateFormatFromTemplate("EEEEdMMMM")
    let number = NumberFormatter(); number.locale = locale; number.numberStyle = .decimal
    let n1 = number.string(from: 6000) ?? "", n2 = number.string(from: 1234.5) ?? ""
    print([id, time.string(from: date), day.string(from: date), weekday.string(from: date),
           month.string(from: date), n1, n2].joined(separator: "\t"))
}

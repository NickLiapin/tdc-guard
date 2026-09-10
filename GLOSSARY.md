# Glossary / Словарь

The same terms are used in the code output, the logs, the diary and the
article. English is this repository's primary language; the Russian column
is for readers of the Russian article.

| English | Russian | Meaning |
|---|---|---|
| window | окно | one machine over one hour; everything it did in that hour |
| labelled window | размеченное окно | a window containing at least one red-team event |
| red team | красная команда | the people who staged the attack at LANL; their events are the ground truth |
| lateral movement | боковое движение | logging in with valid but stolen accounts, machine after machine |
| baseline | опора | a machine's accumulated history: the accounts and destinations already seen on it |
| baseline poisoning | отравление опоры | the intrusion being observed becomes part of the "normal" history |
| baseline drift | устаревание опоры | a frozen baseline no longer knows about new machines |
| baseline scissors | ножницы опоры | refresh it often and it gets poisoned; freeze it and it drifts |
| working days | рабочие сутки | LANL days 8 and 12; all tuning was done on them |
| held-out set (sealed in file names) | отложенный набор | sixteen other days, 3.6M windows, 64 labelled; touched only for final checks |
| false alarms before the N-th hit | ложных до N-й | how many normal windows sit above the N-th labelled one in the ranked list |
| worst rank | худшее место | the rank of the last labelled window |
| AUC | AUC | area under the ROC curve |
| feature | признак | one of the 18 numbers computed per window |
| measurer | измеритель | the code that turns an authentication log into window features (`judge/windows.mjs`) |
| new edge | новое ребро | an account-machine or machine-destination pair never seen before |
| new triple | новая тройка | an event whose three edges (account-source, source-destination, account-destination) are all new |
| moved account | переехавшая учётка | known to the network, but on this machine for the first time |
| fresh account | свежая учётка | never seen anywhere in the network |
| world | мир | one synthetic network described by one `.tdc` config |
| seed | зерно | the number all of the generator's randomness is derived from; same seed, same world, byte for byte |
| training seed | зерно обучения | the same thing for a network's initial state |
| world family | семья миров | one config replicated with six seeds and coincidence shares of 0.5 to 5 percent |
| base world | базовый мир | `gen/world.tdc`, 135 lines, 400k events |
| rich world | богатый мир | 8M events, the attack as a staged process |
| attack stages | стадии нападения | foothold, credential harvesting, spreading, servers; the quiet early stages taught the network to fire on any quiet window |
| clean world | чистый мир | the rich world without attack stages (family `ns`) |
| sparse world | разреженный мир | 18 percent quiet machines whose events are spread over 80-260 hours (family `sp`) |
| coincidence | совпадение | a normal window that happens to carry the full attack signature: many new accounts and many failures |
| coincidence share | доля совпадений | the share of the `isCoin` role in a config, 0.5-5 percent across a family |
| failure storm | шторм отказов | hundreds of failed logins per hour from a broken service; normal according to the labels |
| relocation | переезд | a person moving to another machine and working there all day |
| newcomer | новичок | a fresh account working all day on one machine |
| new host (new machine) | новая машина | a machine with no history: everything on it is legitimately new |
| role | роль | a kind of machine in a config (`isStorm`, `isMove`, `isCoin` and so on) |
| fully connected network | полносвязная сеть | the 1333-weight MLP that looks at a single window |
| recurrent network | рекуррентная сеть | the 4249-parameter LSTM that reads a machine's hours in order |
| SSM | SSM | the state-space model from `net_py/exotic.py` |
| council (ensemble) | консилиум (ансамбль) | several networks whose outputs are combined |
| judge | судья | a small model trained to weigh the council's votes |
| rank averaging | среднее рангов | each network ranks all the windows; a window gets its average rank |
| spread of opinions | разброс мнений | the mean standard deviation of the networks' scores per window; predicts whether an ensemble will help |
| micro-loop | микропетля | look at the top false alarms, find the machine, find the missing role, add two lines to the config |
| attribution ladder | лестница атрибуции | the table that isolates what each factor contributes |
| cost of search / cost curve (also: cost of full recall, cost of the first N hits) | цена поиска (она же цена полноты, цена первых N попаданий) | false alarms as a function of hits found |
| "read N, windows M, labelled K" | "прочитано N, окон M, помеченных K" | what the measurer prints: log lines read, windows produced, windows with a label |

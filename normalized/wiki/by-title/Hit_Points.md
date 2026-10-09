---
title: "Hit Points"
id: "wiki:Hit_Points"
slug: "Hit_Points"
type: "rule"
source_url: "https://swse.miraheze.org/wiki/Bonus_Hit_Points"
canonical_url: "https://swse.miraheze.org/wiki/Hit_Points"
revision_id: "23421"
retrieved_at_utc: "2026-10-09T08:07:37Z"
categories: ["Core Rulebook", "Starships of the Galaxy", "Clone Wars Campaign Guide", "Galaxy at War", "Knights of the Old Republic Campaign Guide", "Web Enhancements"]
duplicates: ["{'file': 'hit-points-d28e079c.md', 'source_url': 'https://swse.miraheze.org/wiki/Hit_Points', 'revision_id': '23421', 'reason': 'byte-identical body (redirect-crawl duplicate)'}", "{'file': 'hit-points.md', 'source_url': 'https://swse.miraheze.org/wiki/Hit_Point', 'revision_id': '23421', 'reason': 'byte-identical body (redirect-crawl duplicate)'}"]
---

# Hit Points

*Reference Books: [[Core_Rulebook]], [[Clone_Wars_Campaign_Guide]], [[Galaxy_at_War]]*

Hit Points (abbreviated "HP") represent two things in the game world: the ability to take physical punishment and keep going, and the ability to turn a serious blow into a graze or near miss. As you become more experienced, you become more adept at parrying strikes, dodging attacks, and rolling with blows, such that you minimize or avoid significant physical trauma, but all this slowly wears you down.

Rather than trying to keep track of the difference between attacks and how much physical injury you take, Hit Points are an abstract measure of your total ability to survive [[Damage]]. As long as you have at least 1 Hit Point, you can act normally on your turn.

A character reduced to 0 Hit Points moves -5 steps on the [[Condition_Track]] and becomes Unconscious (or Disabled). However, if the damage that reduced the creature to 0 Hit Points equals or exceeds its [[Damage_Threshold]], the character instead suffers Death or Destruction (a destroyed [[Droid]], [[Vehicle]], or object cannot be [[Repaired]]).

In the case of a [[Battalion]] being reduced to 0 Hit Points, it [[Disbands]] immediately. Any heroes in the [[Battalion]] appear in the square where the Battalion's was, and if the attack that reduced the [[Battalion]] to 0 Hit Points also exceeded its [[Damage_Threshold]], each hero takes damage equal to the Battalion's lowest [[Attrition]] number. (For example, if an attack reducing a [[Clone_Trooper_Battalion]] to 0 Hit Points also exceeded its [[Damage_Threshold]], each hero would take 21 damage.)

## Falling Unconscious

A creature pushed to the bottom of the [[Condition_Track]] or reduced to 0 Hit Points falls Unconscious. When you fall Unconscious, you fall [[Prone]] and are unable to take any [[Actions]] (see [[Helpless]]). After 1 minute (10 rounds), you make a DC 10 [[Constitution]] check (you can't [[Take_10]]).

On a success, you move +1 step on the [[Condition_Track]], regain consciousness, recover Hit Points equal to your Character Level, and can act normally on your next turn (although you start [[Prone]]). If the check fails, you remain Unconscious for 1 hour, after which you can attempt another [[Constitution]] check. You make a new [[Constitution]] check every hour until you regain consciousness. If you fail by 5 or more points, or if you roll a Natural 1 on your [[Constitution]] check, you suffer Death or Destruction.

If you fail a [[Constitution]] check to regain consciousness, your Condition becomes [[Persistent]], which means you can't heal damage naturally, and you can't use the [[Recover]] Action until you've had [[Surgery]] performed on you, or until you get eight consecutive, uninterrupted hours of rest. An Unconscious character or creature subjected to a [[Coup_de_Grace]] attack or an attack that deals damage equal to or greater than its [[Damage_Threshold]] dies immediately.

A character or creature that receives any kind of healing while Unconscious immediately revives and can get up to fight again (but start [[Prone]]); the healed character or creature has a number of Hit Points equal to the amount of healing it received, and it moves +1 step on the [[Condition_Track]].

### Droids, Vehicles, and Objects

When a [[Droid]], [[Vehicle]], or object is Disabled (the mechanical equivalent of being Unconscious), it moves -5 steps on the [[Condition_Track]], falls [[Prone]], and is unable to take any [[Actions]]. It remains inert and inoperable until [[Repaired]]. The repaired [[Droid]], [[Vehicle]], or object has a number of Hit Points equal to the amount [[Repaired]], and it moves +1 step on the [[Condition_Track]]. A Droid that is [[Repaired]] immediately reactivates and can get up to fight again (but starts [[Prone]]).

A [[Vehicle]] pushed to the bottom of the [[Condition_Track]] is Disabled, and comes to a [[Full_Stop]] immediately. If it was flying in a gravity well at the time it became Disabled, it immediately falls 150 meters (100 squares), plus another 300 meters (200 squares) every round until it either hits the surface, or is [[Repaired]]. Resolve [[Falling_Damage]] as normal.

A [[Starship]] explosion in a hangar can be devastating. An exploding ship deals damage equal to its [[Collision]] damage to any character inside the ship and to characters or objects within 4 squares of the ship.

#### System Damage

*Reference Book: [[Starships_of_the_Galaxy]]*

Some Gamemasters might wish to introduce complications when a ship is disabled from taking damage. Whenever a [[Starship]] is Disabled by being reduced to 0 Hit Points, the ship has a chance of sustaining System Damage requiring emergency repairs. Roll a d20 and refer to the below table; if a system is destroyed, it must be replaced (which can typically be done only at a spaceport or dry dock). If a ship does not receive routine maintenance after twenty hyperspace jumps, roll twice when checking for System Damage.

| D20 | SYSTEM DAMAGE\* |
| --- | --- |
| 1-10 | No system damage |
| 11-15 | Starship becomes "[[Used]]" |
| 16 | Communications/sensors destroyed |
| 17 | Weapons destroyed |
| 18 | [[Hyperdrive]] destroyed |
| 19 | [[Sublight_Drive]] destroyed |
| 20 | Life support destroyed; 2d12 hours of life support remaining |

*\*If a result is not applicable (for example, a [[Used_Starship]] cannot become "more Used"), roll twice and apply both results.*

## Death

A character or creature that dies cannot be brought back to life except under special circumstances (see the [[Revivify]] ability). Similarly, a destroyed [[Droid]], [[Vehicle]], or object cannot be [[Repaired]]. The *Star Wars* galaxy is a vast and perilous wilderness, and heroes who fight against evil and tyranny sometimes make the ultimate sacrifice. When a hero dies, the only thing a player can do is bid their character a fond farewell and roll up a new one.

In the case of a Destroyed [[Vehicle]] containing occupants, those characters take damage equal to one-half the amount that exceeded the Vehicle's [[Damage_Threshold]].

### Spending a Force Point

If you are reduced to 0 Hit Points by an attack that deals [[Damage]] equal to or greater than your [[Damage_Threshold]], you can avoid Death or Destruction by immediately spending a [[Force_Point]], even if you spent a [[Force_Point]] earlier in the round. A character who spends a [[Force_Point]] in this fashion remains at 0 Hit Points, moves -5 steps along the [[Condition_Track]], and becomes Unconscious or Disabled.

## Second Wind

If you are reduced to one-half your maximum Hit Points or less, you can [[Catch_a_Second_Wind]] as a [[Swift_Action]]. This Action heals one-quarter of your full Hit Point total (rounded down) or a number of points equal to your [[Constitution]] score, whichever is greater. You can [[Catch_a_Second_Wind]] only once per day. Certain [[Feats]] or [[Talents]] may allow you to Catch a Second Wind more often, but never more than once in a single encounter.

Only Heroic characters can Catch a Second Wind; [[Vehicles]], [[Beasts]], [[Nonheroic]] characters, objects, and devices cannot.

*Exception:* A [[Nonheroic]] character that takes the [[Extra_Second_Wind]] feat can catch a Second Wind once per day.

## Natural Healing

A living creature that gets eight consecutive, uninterrupted hours of rest regains Hit Points equal to its Character Level. A living creature cannot heal naturally if it has any [[Persistent_Conditions]], and a creature can only benefit from Natural Healing once in a 24-hour period.

In addition to the Hit Points gained from Natural Healing, a creature can regain additional Hit Points from [[First_Aid]] or [[Long-Term_Care]].

## Bonus Hit Points

*Reference Book: [[Knights_of_the_Old_Republic_Campaign_Guide]]*

Bonus Hit Points can come from a variety of sources, like the Duty Bound Species Trait of the [[Massassi]] or the Noble's **[[Bolster_Ally]]** Talent. When a creature gains Bonus Hit Points, they gain a temporary pool of Hit Points that acts as a short-term damage buffer for that creature. Damage is subtracted from Bonus Hit Points first, and any Bonus Hit Points remaining at the end of an encounter go away.

If a creature gains Bonus Hit Points from multiple sources, the creature uses only the larger amount of Bonus Hit Points from the two sources. For example, if a creature has 10 Bonus Hit Points and another ability gives it 15 Bonus Hit Points, that creature then has 15 Bonus Hit Points. If the new ability would only give the creature 5 Bonus Hit Points, it keeps the 10 Bonus Hit Points it already has instead.

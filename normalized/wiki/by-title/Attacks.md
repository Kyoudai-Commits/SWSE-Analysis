---
title: "Attacks"
id: "wiki:Attacks"
slug: "Attacks"
type: "rule"
source_url: "https://swse.miraheze.org/wiki/Critical_Hit"
canonical_url: "https://swse.miraheze.org/wiki/Attacks"
revision_id: "27406"
retrieved_at_utc: "2026-10-09T08:06:26Z"
categories: ["Core Rulebook", "Clone Wars Campaign Guide", "Knights of the Old Republic Campaign Guide", "Web Enhancements"]
images: ["File:Burst.webp", "File:Splash.webp", "File:Cone.webp"]
duplicates: ["{'file': 'attacks-559737eb.md', 'source_url': 'https://swse.miraheze.org/wiki/Area_Attacks', 'revision_id': '27406', 'reason': 'byte-identical body (redirect-crawl duplicate)'}", "{'file': 'attacks-56de5a6c.md', 'source_url': 'https://swse.miraheze.org/wiki/Splash', 'revision_id': '27406', 'reason': 'byte-identical body (redirect-crawl duplicate)'}", "{'file': 'attacks-5dda7d93.md', 'source_url': 'https://swse.miraheze.org/wiki/Burst', 'revision_id': '27406', 'reason': 'byte-identical body (redirect-crawl duplicate)'}", "{'file': 'attacks-91867a20.md', 'source_url': 'https://swse.miraheze.org/wiki/Shield_Rating', 'revision_id': '27406', 'reason': 'byte-identical body (redirect-crawl duplicate)'}", "{'file': 'attacks-cda3bfe1.md', 'source_url': 'https://swse.miraheze.org/wiki/Area_Attack', 'revision_id': '27406', 'reason': 'byte-identical body (redirect-crawl duplicate)'}", "{'file': 'attacks-fe9c1347.md', 'source_url': 'https://swse.miraheze.org/wiki/Critical_Hits', 'revision_id': '27406', 'reason': 'byte-identical body (redirect-crawl duplicate)'}", "{'file': 'attacks.md', 'source_url': 'https://swse.miraheze.org/wiki/Autofire', 'revision_id': '27406', 'reason': 'byte-identical body (redirect-crawl duplicate)'}"]
---

# Attacks

*Reference Books: [[Core_Rulebook]], [[Clone_Wars_Campaign_Guide]]*

Attacking (whether it be [[Melee_Attacks]], [[Ranged_Attacks]], or [[Vehicle_Attacks]]) is a [[Standard_Action]]. When you make an attack roll, roll 1d20 and add the appropriate modifiers. If your result is equal to or higher than the target's [[Reflex_Defense]], you hit and deal Damage (see below).

**Melee Attack: 1d20 + [[Base_Attack_Bonus]] + [[Strength]] Modifier**

**Ranged Attack: 1d20 + [[Base_Attack_Bonus]] + [[Dexterity]] Modifier + [[Range]] Modifier**

**Vehicle Attack: 1d20 + [[Base_Attack_Bonus]] + Vehicle's [[Intelligence]] Modifier + Weapon [[Range]] Modifier**

- *[[Base_Attack_Bonus]]:* Your [[Heroic_Class]] and level determine your [[Base_Attack_Bonus]].
  - If you are [[Trained]] in the [[Pilot]] skill, you gain a +2 bonus on Vehicle Attacks made with [[Weapon_Systems]] identified as being crewed by the [[Vehicle_Pilot]].
- *[[Strength]] Modifier:* [[Strength]] helps you swing a weapon harder and faster, so your [[Strength]] modifier applies to melee attack rolls.
- *[[Dexterity]] Modifier:* Since [[Dexterity]] measures coordination and steadiness, your [[Dexterity]] modifier applies to attacks with ranged weapons.
- *[[Intelligence]] Modifier:* A Vehicle's computer improves the accuracy of the Vehicle's [[Weapon_Systems]], and the Vehicle's [[Intelligence]] score measures the quality of the computer.
- *[[Range]] Modifier:* A ranged weapon can attack a target at Point-Blank, Short, Medium, or Long [[Range]]. If you make a ranged attack against a target within the weapon's Point-Blank Range, you take no penalty on the attack roll; your penalty on attack rolls increases to
  - -2 at Short Range,
  - -5 at Medium Range,
  - and -10 at Long Range.

## Damage

When you hit with an Attack, you deal Damage that reduces the enemy's [[Hit_Points]].

**Melee Damage: Weapon Dice + One-Half Heroic Level (Rounded Down) + [[Strength]] Modifier**

**Ranged Damage: Weapon Dice + One-Half Heroic Level (Rounded Down)**

**Vehicle Damage: (Weapon Damage + 1/2 Pilot's Heroic Level + Miscellaneous Modifiers) x Damage Multiplier**

- *Weapon Dice:* A hit always deals at least 1 point of Damage, even if penalties to damage bring the Damage result below 1.
- *One-Half Heroic Level:* Weapons are simply more dangerous in the hands of powerful heroes (and villains).
  - Beasts add half their [[Beast]] Level (rounded down) to damage rolls made with Natural Weapons.
- *[[Strength]] Modifier:* When you hit with a Melee or Thrown Weapon, you add your [[Strength]] modifier to Damage.
  - When you hit with a melee weapon that you are wielding two-handed, you add double your [[Strength]] bonus (if any) to the Damage. This higher [[Strength]] modifier does not apply to two-handed melee attacks with [[Light_Weapons]].
- *Damage Multiplier:* After rolling the weapon damage dice, multiply the result by the listed Damage Multiplier. For example, when you fire a [[Vehicle_Weapon]] that deals 6d10x2 damage, roll 6d10 and multiply the result by 2.

### Damage Reduction

A creature or object with Damage Reduction (DR) ignores a certain amount of Damage every Attack. The amount of Damage it ignores is always indicated; for example, an object with DR 10 ignores the first 10 points of damage from each attack.

Damage Reduction is sometimes bypassed by one or more specific damage types (noted after the DR value). For example, a creature with DR 5/Energy ignores 5 points of damage from any source except one that deals Energy damage (such as from a blaster). Similarly, a creature with DR 10/Piercing or Slashing ignores 10 points of damage from any source except one that deals Piercing or Slashing damage. [[Lightsabers]] ignore Damage Reduction unless specifically noted otherwise.

Certain [[Talents]] grant Damage Reduction. When a character with multiple types of Damage Reduction takes damage, use whichever Damage Reduction value most benefits the character, based on the type of Damage. For example, if a character with DR 1 and DR 10/Energy is struck by a blaster, it's better for the character to apply their DR 1 against the attack (since DR 10/Energy is bypassed by a blaster).

### Shield Rating

Some [[Droids]], [[Vehicles]], and devices have a Shield Rating (SR). Whenever a target with SR takes Damage from an Attack, reduce the damage by the Shield Rating. The remaining damage (if any) is dealt to the target's [[Hit_Points]], subtracting Damage Reduction normally.

If the Damage dealt by an attack exceeds the target's SR, reduce the Shield Rating by 5. This reduction is cumulative, so a target's Shield Rating can eventually be reduced to zero.

A character may recharge the shields of a device or [[Vehicle]] by spending three [[Swift_Actions]] on the same or consecutive rounds to make a DC 20 [[Mechanics]] check; if the check succeeds, the target's SR improves by 5 points (up to its normal maximum). A [[Droid]] may recharge its own shields by spending three [[Swift_Actions]] on the same or consecutive rounds to make a DC 20 [[Endurance]] check; if the check succeeds, its current Shield Rating improves by 5 points (up to its normal maximum).

### Mixed Damage Types

*Reference Book: [[Knights_of_the_Old_Republic_Campaign_Guide]]*

Some weapons and effects deal damage with multiple damage types; for example, [[Lightsabers]] deal Energy and Slashing damage, and [[Bowcasters]] deal Energy and Piercing damage. Whenever a weapon or effect has multiple damage types, if the effect deals both types of damage simultaneously then any other ability that depends on one of the effect's damage types applies to the full damage from that effect.

So, for example, the *[[Negate_Energy]]* Force Power can be used to negate the full damage from a [[Lightsaber]] attack since it can negate Energy damage. Similarly, the special function of [[Fiber_Armor]] can be used to grant the wearer DR 10 against an attack from a [[Bowcaster]], since the [[Bowcaster]] is considered to be a ranged Energy weapon.

## Critical Hits

When you roll a Natural 20 on your attack roll (the d20 comes up "20"), the attack automatically hits, no matter how high the defender's [[Reflex_Defense]]. In addition, you score a Critical Hit and deal double damage. All targets are subject to Critical Hits, even inanimate objects. A Natural 20 on an Area Attack roll automatically hits all targets within the affected area, but Area Attacks do not deal double damage on a Critical Hit.

In [[Mass_Combat]], if an attacker making a non-Area Attack against a [[Battalion]] rolls a Natural 20, the target [[Battalion]] is automatically hit and takes full damage from the attack instead of half damage. If an attacker making an Area Attack rolls a Natural 20, it is still an automatic hit, but the damage remains the same.

### Automatic Misses

When you roll a Natural 1 on your attack roll (the d20 comes up "1"), the attack automatically misses, no matter how high the bonus on the attack roll is. Effects that negate an attack (such as **[[Block]]**, **[[Deflect]]**, or [[Vehicular_Combat]]) or cause an attack to automatically miss (such as spending a [[Destiny_Point]]) can also negate a Critical Hit. A Natural 1 on an attack against a [[Battalion]] is always a miss.

## Area Attacks

Certain weapons and effects, such as [[Grenades]], Autofire Weapons, or the *[[Force_Slam]]* Force Power, target all creatures in a given area instead of a single target. When you make an Area Attack, you make a single attack roll; if your attack roll is equal to 10 or higher, compare the result to the [[Reflex_Defense]] of every target in the area.

Targets you hit take full damage, and creatures you miss take half damage. A Natural 20 on an Area Attack roll automatically hits all targets within the affected area, but Area Attacks do not deal double damage on a Critical Hit. A character with the **[[Evasion]]** Talent takes half damage from a successful Area Attack, and takes no damage from an Area Attack that that misses their [[Reflex_Defense]].

A target with [[Cover]] or [[Improved_Cover]] takes no damage from Area Attacks if the attack roll is less than the target's [[Reflex_Defense]]. For a Burst or Splash weapon, determine [[Cover]] relative to the center of the weapon's Area of Effect. For an Autofire Weapon, determine [[Cover]] relative to the attacker.

### Types of Area Attacks

Autofire WeaponsBurst WeaponsSplash WeaponsCone Attacks

Any ranged weapon that has an Autofire setting can be set on Autofire as a [[Swift_Action]]. Some weapons, such as the [[E-Web_Repeating_Blaster]], operates only in Autofire mode. You target a 2x2-square area, making a single attack roll at a -5 penalty, and compare the result to the [[Reflex_Defense]] of every creature in the area. Autofire consumes ten shots or slugs, and it can only be used if the weapon has ten shots or slugs in it.

If you are using an Autofire-only weapon, you may Brace your weapon by taking two [[Swift_Actions]] in the same round immediately before making your attack. When you Brace an Autofire-only weapon, you take only a -2 penalty on your attack roll when making an Autofire attack or using the [[Burst_Fire]] feat. Only [[Heavy_Weapons]], [[Rifles]], and [[Pistols]] with an extended [[Retractable_Stock]] can be Braced.

If your [[Vehicle]] is capable of Autofire, you can use it to make an Area Attack in [[Character_Scale]], just as in Character Combat.

## Strafing Attacks

Instead of attacking a 2x2-Square area, [[Airspeeders]] and [[Starfighters]] may attack a number of squares in a straight line as they fly over them. Doing this requires the [[Attack_Run]] Action, and the Area Attack applies to a straight line 1 square wide, and 5 to 10 squares long. You take a penalty to your attack roll equal to the number of squares included in the Area Attack.

You cannot make a Strafe Attack in [[Starship_Scale]].

[[Grenades]] and [[Explosives]] usually have a Burst radius. When you make an Area Attack with such a weapon, you must decide where to center the Burst before you make the attack roll. The center of a Burst is always the corner of a square (at the "Crosshairs").

The Red Squares are a 1-Square Burst. The Blue Squares are a 2-Square Burst. The Green Squares are a 3-Square Burst. The Yellow Squares are a 4-Square Burst.

Some weapons have a Splash radius. When you make an attack against a target, that target takes full damage if your attack roll exceeds its [[Reflex_Defense]], and half damage if the attack misses. Also compare your attack roll against the [[Reflex_Defense]] of every target adjacent to the primary target; these adjacent targets take half damage if the attack hits, or no damage if the attack misses.

The red square is no Splash. Blue Squares are 1-Square Splash. X Splash means you have a circle with Radius X. That means the Green Squares are Radius 2, the Yellow Squares are Radius 3, and the Purple Squares are Radius 4.

Weapons that attack in a 6-Square "Cone" start at an intersection on the battle grid (one of the corners of your space) and then extend outward for 6 squares in a 90-degree arc. Unlike normal range calculations, however, count diagonals using the old method- that is, 1 square for the first and all odd diagonals, and 2 squares for the second and all even diagonals.

### Special Rules

Vehicle CombatMass Combat

Because of the size of each square compared to the size of [[Starships]], Area Attacks (including Autofire, Burst, and Splash weapons) are resolved as attacks on a single target in [[Starship_Scale]], unless the weapon is specifically listed as having a Starship-scale Area Attack.

Since [[Battalions]] take half damage from non-Area Attacks, Area Attacks are a more efficient way to deal damage to them. Area Attacks target only a single [[Starship_Scale]] square unless otherwise specified. Thus, a [[Clone_Trooper_Battalion]] can make [[Autofire]] attacks using their [[Blaster_Rifles]], but only against a single square.

When you make an Area Attack in [[Mass_Combat]], you select a single square within [[Range]], make an attack roll, and compare the result to the [[Reflex_Defense]] of each [[Battalion]] and [[Vehicle]] in the target square. If both ground and flying [[Battalions]] occupy the same square, you must choose to make the attack against air units or ground units, but not both.

If the attack roll is higher than a Battalion's [[Reflex_Defense]], that [[Battalion]] takes full damage from the Area Attack. The [[Battalion]] takes no damage on a miss if the attack was made with a [[Character_Scale]] weapon, or half damage on a miss if the attack was made with a [[Starship_Scale]] weapon.

## Maiming Foes

*Reference Book: [[Web_Enhancements]] ([[Saga_Edition_FAQ]] (E18))*

A character may attempt to cripple an opponent instead of killing them. To do so, the character must declare their intent ahead of time and make an Attack at a -5 penalty, dealing half Damage on a successful attack. Should the resulting attack take their foe to 0 [[Hit_Points]] while still overcoming the target's [[Damage_Threshold]] (effectively killing them) the target is instead Maimed in some manner, but otherwise alive. You sever one of your target's arms at the wrist or elbow joint, or one of the target's legs at the knee or ankle joint (your choice).

Severing part of an arm prevents the target from wielding weapons or using tools in that hand, and imposes a -5 penalty on [[Skill_Checks]] and [[Ability_Checks]] keyed to [[Strength]] and [[Dexterity]]. Severing part of a leg knocks the target [[Prone]], reduces the target's [[Speed]] by half, reduces its [[Carrying_Capacity]] by half, and imposes a -5 penalty on [[Skill_Checks]] and [[Ability_Checks]] keyed to [[Strength]] and [[Dexterity]].

Because of the severity of such an injury, losing part of a limb causes a [[Persistent_Condition]] that can only be removed by having [[Surgery]] successfully performed on you. A [[Cybernetic_Prosthesis]] negates these reductions and penalties.

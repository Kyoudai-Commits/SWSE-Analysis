---
title: "Use Computer (Int) — Applications"
parent_title: "Use Computer (Int)"
id: "wiki:Use_Computer#000"
type: "skill"
parent: "wiki:Use_Computer"
heading: "Applications"
heading_path: ["Use Computer (Int)", "Applications"]
source_url: "https://swse.miraheze.org/wiki/Use_Computer#Applications"
revision_id: "27333"
categories: ["Core Rulebook", "Starships of the Galaxy", "Scum and Villainy", "Legacy Era Campaign Guide"]
---

# Applications

The following are the primary applications of the Use Computer skill.

Getting information through a computer requires you to connect to the appropriate network (such as the HoloNet, or its equivalent in other eras) and locate the files you seek. Connecting to an Indifferent, Friendly, or Helpful network (a [[Full-Round_Action]]) doesn't require a skill check if you are using a computer that's already linked to it; however, establishing a connection to a network using a remote computer requires a DC 10 Use Computer check. You can also get information without connecting to a network if you use a computer whose memory contains that information; the GM decides what information a computer's memory actually holds.

Finding information on a single topic requires a set amount of time (see below); at the end of this time, you must make a Use Computer check. The time required and the check DC are determined by the type of information sought.

For example, locating general information about a senator is easier than locating specific information (such as the senator's date of birth), which is easier than finding private information (such as the senator's private comm channel code), which is easier than uncovering secret information (such as the senator's cred stick code).

| INFORMATION | DC | TIME REQUIRED |
| --- | --- | --- |
| General | 15 | 1 Minute (10 Rounds) |
| Specific | 20 | 10 Minutes |
| Private | 25 | 1 Hour |
| Secret\* | 30 | 1 Day (8 Hours) |

*\*Secret information can only be accessed on a computer that is Helpful to you.*

**Trained Only:** Moving from a given location to a desired destination through hyperspace requires a successful Use Computer check. Because every object in the galaxy is constantly in motion, the precise path between two locations changes from day to day. If the Astrogator uses current data (one day old at most), they can plot a safe course. Doing so usually requires 1 minute, at the end of which you must succeed on a DC 10 Use Computer check (without data with which to plot a jump through hyperspace, the base DC for the Use Computer check is 30, and requires 1 hour calculating coordinates and vectors before attempting the check). As a general rule, data for a particular route through hyperspace is available to anyone with access to [[The_HoloNet]]- although that data might be outdated if the route in question is not frequently traveled by other ships.

The difficulty of plotting a course through hyperspace is determined by how recently you have updated your Astrogation data, as shown on the table below.

| ASTROGATION DC | AGE OF ASTROGATION DATA |
| --- | --- |
| 10 | Less than 1 day |
| 15 | At least 1 day, but less than 1 standard week (5 days) |
| 20 | At least 1 week, but less than 1 standard month (35 days) |
| 25 | At least 1 month, but less than 1 standard year (368 days) |
| 30 | At least 1 year |

Additionally, you may choose to plot a hyperspace course more aggressively than normal, reducing your travel time by increasing the chance of something going wrong. For every 5 points by which you increase the Use Computer check DC, you may reduce your travel time by 1 day; if this would reduce the travel time to less than 1 day, you instead reduce the remaining travel time by one-half, to a minimum of 1 hour. You must make the decision to increase the Use Computer check DC before making the check. Alternatively, you may gain a +5 circumstance bonus on your Use Computer check if you voluntarily double the travel time.

Certain situations or circumstances can also modify the check, as shown in the table below. The lack of a [[Navicomputer]] (or, failing that, an Astromech Droid with stored coordinates) makes the task much more difficult. If time is of the essence, the Astrogator can perform the check as a [[Full-Round_Action]] by taking a -10 penalty on their Use Computer check.

Astrogation DC Modifiers

| SITUATION | CHECK MODIFIER |
| --- | --- |
| Using [[Navicomputer]] | +5 |
| No [[Navicomputer]] Used\* | -10 |
| No HoloNet Access | -5 |
| Attempt to make the check in 1 round | -10 |

*\*Do not apply the penalty if the ship has current Astrogation data stored in an Astromech Droid or receives accurate transmitted data from another ship.*

If the Use Computer check is successful, the [[Starship]] enters hyperspace without incident and arrives at its destination in a number of days equal to 1d6 x the Starship's [[Hyperdrive]] multiplier.

A failed Use Computer check indicates that the Astrogator has made a potentially dangerous error in their calculations. Make another Use Computer check using the same modifier against the same DC. If this second Use Computer check is successful, the error is caught before entering hyperspace, and the process of plotting a course must begin anew. If this second Use Computer check fails, the [[Starship]] moves -1 [[Persistent]] step on the [[Condition_Track]] and takes damage equal to 5% of its total [[Hit_Points]] for every point by which the check fails. (The [[Persistent_Condition]] and damage remain until the ship undergoes maintenance.) If the ship is not [[Disabled]] or destroyed, it arrives at the intended destination in double the expected travel time. If the ship is [[Disabled]], it drops out of hyperspace in a random location somewhere between the point of origin and the destination (the exact location is determined by the GM).

A [[Navicomputer]] allows a character aboard a Starship to make a Use Computer check to Astrogate [[Untrained]].

Space HazardsSpace Hazards

*Reference Book: [[Scum_and_Villainy]]*

Traveling in space is a dangerous proposition under the best circumstances, and travel through hyperspace carries its own set of perils. Ordinarily, the Gamemaster chooses where in a Starship's journey a mishap occurs, and, thus, just how far away the ship is from any hope of rescue or assistance.

Space travel hazards can arise when a [[Starship]] is [[Disabled]] because of a poorly plotted hyperspace course. The Gamemaster can use the following table to determine exactly what mishap befalls the vessel. The Gamemaster should roll a d20 to determine the severity of the Space Hazard, then another d20 to determine a specific mishap.

| D20 ROLL | HAZARD | MISHAP |
| --- | --- | --- |
| 1-8 | MINOR (D20 ROLL) | |
|  | 1-8 | The [[Starship]] passes through an uncharted dust cloud, clogging sensors and communications equipment. The Use Sensors application of the Use Computer Skill takes a -5 penalty for every 5 squares between the user and the sensor target (instead of the usual -5 per 10 squares penalty). |
| 9-14 | The [[Starship]] encounters space debris, setting off a collision alarm. The [[Vehicle_Pilot]] must make a DC 15 [[Pilot]] check to [[Avoid_Collision]] with a Huge piece of debris; the DC increases by 1 for each round between the alarm sounding and the [[Pilot]] check. |
| 15-18 | The [[Starship]] approaches a gravity field too quickly, causing structural stress. The Starship's Armor bonus is reduced by 1 until all [[Persistent_Conditions]] are removed. |
| 19-20 | The [[Starship]] passes too close to a supernova, overloading computer systems with solar radiation. Use Computer checks aboard the [[Starship]] take a -5 penalty until all [[Persistent_Conditions]] are removed. |
| 9-14 | MODERATE (D20 ROLL) | |
|  | 1-8 | The [[Starship]] passes through a dense, uncharted dust cloud, clogging sensors and communications equipment. The Use Sensors application of the Use Computer Skill takes a -5 penalty for every 2 squares between the user and the sensor target (instead of the usual -5 per 10 squares penalty). |
| 9-14 | The [[Starship]] encounters an uncharted asteroid field, setting off a collision alarm. The [[Vehicle_Pilot]] must make a DC 15 [[Pilot]] check to [[Avoid_Collision]] with a Gargantuan piece of debris; the DC increases by 2 for each round between the alarm sounding and the [[Pilot]] check. |
| 15-18 | The [[Starship]] enters an area of high radiation, causing the sensors to report false contacts (and dropping the ship out of hyperspace to avoid a [[Collision]]). The Starship's navigator must plot a new course out of the radiation field, with a -5 penalty on the Use Computer check. |
| 19-20 | The [[Starship]] passes through an unexpected gravity field, causing structural stress. The Starship's Armor bonus is reduced by 2 until all [[Persistent_Conditions]] are removed. |
| 15-19 | MAJOR (D20 ROLL) | |
|  | 1-6 | The [[Starship]] encounters a dense, uncharted asteroid field, setting off a collision alarm. The [[Vehicle_Pilot]] must make a DC 15 [[Pilot]] check to [[Avoid_Collision]] with a Colossal piece of debris; the DC increases by 5 for each round between the alarm sounding and the [[Pilot]] check. |
| 7-10 | The [[Starship]] passes through a superdense, uncharted dust cloud, clogging sensors and communications equipment. The Use Sensors application of the Use Computer Skill takes a -5 penalty for every square between the user and the sensor target (instead of the usual -5 per 10 squares penalty). |
| 11-13 | The [[Starship]] encounters another Starship's dumped cargo, setting off a collision alarm. The [[Vehicle_Pilot]] must make a DC 15 [[Pilot]] check to [[Avoid_Collision]] with a Huge piece of debris; the DC increases by 1 for each round between the alarm sounding and the [[Pilot]] check. If the [[Vehicle_Pilot]] avoids the [[Collision]], the cargo might be salvageable, it consists of 10d10 tons of cargo, each with a value of 10d10x10 credits. |
| 14-15 | The [[Starship]] encounters a Colossal vessel with a disabled [[Hyperdrive]], setting off a collision alarm. The [[Vehicle_Pilot]] must make a DC 15 [[Pilot]] check to [[Avoid_Collision]]; the DC increases by 5 for each round between the alarm sounding and the [[Pilot]] check. At the Gamemaster's discretion, the crew of the other vessel might be alive and in need of assistance (or helpless to prevent being boarded and plundered). |
| 16-17 | The [[Starship]] skirts the edge of a black hole, causing the intense gravity to warp the vessel's structural integrity. The Starship's Armor bonus is reduced by 5 until all [[Persistent_Conditions]] are removed. |
| 18-19 | The [[Starship]] flies through a superdense cluster of stars, the stress of which causes the [[Hyperdrive]] to burn up. The Starship's [[Hyperdrive]] is disabled and requires a DC 30 [[Mechanics]] check to repair to a Class 15. |
| 20 | The [[Starship]] nearly collides with a massive gas giant, corroding the ship's hull plating and causing the ship to take an additional 10% of its total [[Hit_Points]] in damage. |
| 20 | REROLL ON THE TABLE ABOVE TWICE. | |

When the heroes have a space encounter, the effects should be dealt with in one of several ways. Under the rules for hyperspace hazards in the *[[Core_Rulebook]]* (see above), the ship takes damage and moves down the [[Condition_Track]] with a [[Persistent_Condition]]. Under normal rules, the [[Hit_Points]] can be restored and the [[Condition]] can be removed with an hour's work and a [[Mechanics]] check. Some of the Space Hazards listed above also have their own [[Skill_Checks]] associated with them.

Alternatively, the Gamemaster can require that the effects of the Space Hazards cannot be dealt with except by a more challenging [[Skill_Check]] or a series of [[Skill_Checks]], and Gamemasters should feel free to use the sample skill DCs (see the [[Job_Generator]]) to determine the difficulty of clearing the effects of the Hazard. As a general rule, Minor Hazards should use the Medium DCs, Moderate Hazards should use the Moderate DCs, and Major Hazards should use the Hard DCs.

For example, when a ship passes through an uncharted dust cloud, the GM can call for a Use Computer check to calibrate the ships sensors; alternatively, the GM could require a hero to physically leave the ship and clean the sensors manually, which could involve [[Acrobatics]] or [[Climb]] checks to perform the task in [[Zero-Gravity]].

**Trained Only:** If you are [[Trained]] in Use Computer, you can disable or erase a program on a computer that is Helpful toward you. Disabling or erasing a program takes 10 minutes and requires a DC 15 Use Computer check.

**Trained Only:** As a [[Full-Round_Action]], you can make a Use Computer check to adjust the attitude of a computer in order to gain access to its programs and information. You must be able to communicate with the computer either through a direct interface (such as a keypad) or by connecting to it through an appropriate network (such as the HoloNet). Apply a modifier on the check based on the computer's current attitude toward you: Hostile -10, Unfriendly -5, Indifferent -2, Friendly +0.

If the check equals or exceeds the computer's [[Will_Defense]], the computer's Attitude shifts one step in your favor. If you fail, the computer's Attitude does not change. If you fail by 5 or more, the computer's Attitude becomes one step worse (for example, Indifferent to Unfriendly) and the computer notifies the computer's administrator of the access attempt.

A Hostile computer can be dangerous. If the computer becomes Hostile or you fail any Use Computer check made to Improve Access to a Hostile computer, it traces your exact location and notifies the nearest security personnel. In addition, if you fail by 5 or more when attempting to Improve Access to a Hostile computer, it isolates your connection and rejects any further attempts you make to access it for 24 hours.

As a [[Standard_Action]], you can Issue a Routine Command to a Friendly or Helpful computer. Examples include turning a computer on or off, viewing and editing documents or recordings in its memory, printing a hard copy of a document or image on a flimsiplast sheet, opening or closing doors that the computer controls, and the like.

Issuing Routine Commands doesn't normally require a Use Computer check. However, if another character issues a contradictory command, the computer follows the command of the character toward whom it has a better Attitude (for example, it follows a command from someone toward whom it is Helpful over someone toward whom it is Friendly).

If the computer has the same Attitude toward both characters, make an opposed Use Computer check against the competing character. If you succeed, your command takes effect. If you fail, the opposing character's command takes effect.

**Trained Only:** You can Reprogram a [[Droid]] to obey a new master, copy data stored in its memory banks, change its [[Trained_Skills]] and other abilities, erase memories selectively or entirety (resetting the [[Droid]] to its factory preset status). Reprogramming a Droid takes 10 minutes. Reprogramming requires that the Droid be shut down for the duration of the procedure (or see "Self-Programming" below).

Reprogramming [[Feats]] and [[Talents]] are more difficult, with a DC equal to the Droid's [[Will_Defense]] and 30 minutes of uninterrupted work, and attempts suffer a -5 penalty on your Use Computer check. Furthermore, [[Feats]] and [[Talents]] can only be Reprogrammed if they are neither a requirement for any of the Droid's [[Prestige_Classes]] nor a prerequisite for any [[Feat]] or [[Talent]] the Droid retains. As always, a Droid must meet all prerequisites for any replacement [[Feats]] or [[Talents]].

- A [[Droid]] can only have [[Talents]] it is eligible for based on its [[Classes]]; thus, a Droid with 5 levels in the [[Soldier]] Class could only be Reprogrammed with 3 [[Soldier_Talents]] (from [[Soldier]] levels 1, 3, and 5). A Droid with 5 levels of [[Soldier]] and 3 levels of [[Scoundrel]] could be Reprogrammed with 3 [[Soldier_Talents]] and 2 [[Scoundrel_Talents]].
- To Reprogram a [[Trained_Skill]], the programmer must be [[Trained]] in that [[Skill]] or purchase a skill package (100 credits). To Reprogram a [[Feat]] or [[Talent]], the programmer must either have that [[Feat]] or [[Talent]], or purchase a feat or talent package (1,000 credits).

If the Droid's owner is unable to do the Reprogramming themselves, they can hire a professional programmer to do the task for them. The standard cost of hiring a programmer is (Droid's [[Will_Defense]] squared) x 10 credits for a [[Skill]], or 10 times this amount for a [[Feat]] or [[Talent]]. This cost includes any necessary [[Skill]], [[Feat]], or [[Talent]] package.

A Droid [[Trained]] in Use Computer may attempt to reprogram itself. However, the Droid must have the appropriate [[Skill]], [[Feat]], or [[Talent]] package to do so, and it takes a -5 penalty on its skill check. A Droid attempting to Self-Reprogram does not have to be shut down, but it is [[Helpless]] and unable to take any [[Actions]] until the attempt is completed.

Although intelligent [[Droids]] consider it frightful and ghoulish and a fate worse than death, the Memory Wipe is a fact of existence for most [[Droids]]. Its primary purpose is to eradicate personality quirks that distinguish an [[Independent_Droid]]. Wiping a Droid's memory requires a successful Use Computer check against the Droid's [[Will_Defense]]. The [[Droid]] must be shut down to perform the Memory Wipe.

A Memory Wipe erases one Class Level per minute. A complete Memory Wipe reduces a Droid to a basic model with no personality quirks and no class abilities. For example, a [[3PO-Series_Protocol_Droid]] that had been a 1st-level [[Nonheroic]]/4th-level [[Scoundrel]] becomes a 1st-level [[Nonheroic]] basic model after a 4-minute Memory Wipe, losing its Heroic Levels and all corresponding benefits.

Unlike organic beings, Droids have a form of mechanical immortality: if a Droid's programming is saved to a computer system, and a new chassis and Droid Brain can be bought or found, others can attempt to load its memory into the new chassis and reactivate the [[Droid]]. A successful Use Computer check is required to transfer a Droid's programming into a new chassis. The DC for the Use Computer checks depends on the type of new chassis being used:

| CHASSIS TYPE | DC |
| --- | --- |
| Same Model | 20 |
| Different Model, Same Degree | 25 |
| Different Model, Different Degree | 35 |

Each time the transfer is attempted, the Droid must make a DC 15 [[Intelligence]] check. A failed check indicates that the Droid's memory suffers corruption: a permanent reduction of 1d6 [[Intelligence]]. The corrupted programming can't be repaired; if the Droid's [[Intelligence]] modifier decreases because of corruption, the Droid's [[Trained_Skills]] must be reduced accordingly. The Droid also loses access to [[Feats]] that have an [[Intelligence]] prerequisite higher than the Droid's new [[Intelligence]] score.

A Droid successfully transferred into another Droid of the same model resumes functioning as it was before the transfer, retaining all Class Levels, [[Ability_Scores]], [[Skills]], [[Feats]], and [[Talents]].

A Droid successfully transferred into a different model adopts the [[Strength]] and [[Dexterity]] of the new model but keeps its previous [[Intelligence]], [[Wisdom]], and [[Charisma]] scores. The Droid retains its [[Trained_Skills]], although skill modifiers based on [[Strength]] and [[Dexterity]] might need adjusting. Finally, the Droid losses one Class Level (including all associated [[Talents]] and [[Feats]]) as it has to reprogram and adapt its memory and sensory inputs for the new chassis.

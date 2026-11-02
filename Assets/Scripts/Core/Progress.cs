using System.Collections.Generic;
using UnityEngine;

namespace NightClass
{
    public enum Difficulty { Ghost = 0, Normal = 1, Hard = 2 }

    /// <summary>Puzzle progress for the current run (used for hints).</summary>
    public static class Progress
    {
        public static bool TrapdoorOpen, PlanksBroken, TorchTaken, FireOut, NoteTaken, GarageOpen;
        public static bool RubbleCleared, SafeKeyTaken, SafeOpen, ElevatorFixed, MainKeyTaken, HammerTaken;

        public static void Reset()
        {
            TrapdoorOpen = PlanksBroken = TorchTaken = FireOut = NoteTaken = GarageOpen = false;
            RubbleCleared = SafeKeyTaken = SafeOpen = ElevatorFixed = MainKeyTaken = HammerTaken = false;
        }

        public static string Hint()
        {
            var list = new List<string>();
            if (!PlanksBroken && !HammerTaken) list.Add("The main door is boarded up. A hammer is kept in the gym storage room.");
            if (!PlanksBroken && HammerTaken) list.Add("Use the hammer on the planks across the main entrance.");
            if (!TrapdoorOpen) list.Add("The janitor's room has a hatch in the floor. Push it open to reach the basement.");
            if (TrapdoorOpen && !TorchTaken) list.Add("It's dark in the basement. A burning torch hangs on the wall down there.");
            if (!FireOut) list.Add("A fire blocks the west corridor. The sprinkler valve is in the toilets.");
            if (FireOut && !NoteTaken) list.Add("The principal's office is past the fire. Search the desk.");
            if (NoteTaken && !GarageOpen) list.Add("The note has the garage code. The keypad is at the east end of the corridor.");
            if (GarageOpen && !RubbleCleared) list.Add("Dynamite from the garage can clear the rubble in the basement.");
            if (RubbleCleared && !SafeKeyTaken) list.Add("Something shines in the boiler room behind the rubble.");
            if (SafeKeyTaken && !SafeOpen) list.Add("The safe in the teachers' lounge takes that key.");
            if (SafeOpen && !ElevatorFixed) list.Add("The spring fits the broken food elevator in the cafeteria.");
            if (ElevatorFixed && !MainKeyTaken) list.Add("The main key came down with the food elevator.");
            if (MainKeyTaken) list.Add("Take the main key to the entrance.");
            list.Add("Hide in a locker or wardrobe when you hear her coming.");
            list.Add("A burning torch scares her away for 30 seconds.");
            list.Add("Dropped things make noise. She comes to check.");
            int n = Mathf.Min(2, list.Count);
            return list[Random.Range(0, n)];
        }
    }
}

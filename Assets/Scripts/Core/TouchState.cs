using UnityEngine;

namespace GridProto
{
    /// <summary>Input shared between the on-screen controls and the player.</summary>
    public static class TouchState
    {
        /// <summary>Joystick direction, -1..1 on both axes.</summary>
        public static Vector2 Move;

        /// <summary>Screen pixels dragged on the look area since the player last read it.</summary>
        public static Vector2 LookDelta;

        public static bool JumpPressed;
        public static bool CrouchPressed;
        public static bool InteractPressed;

        public static void Clear()
        {
            Move = Vector2.zero;
            LookDelta = Vector2.zero;
            JumpPressed = false;
            CrouchPressed = false;
            InteractPressed = false;
        }
    }
}

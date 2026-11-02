using UnityEngine;

namespace NightClass
{
    public enum ItemType { None = 0, MainKey = 1, Hammer = 2, Torch = 3, CodeNote = 4, SafeKey = 5, Spring = 6, Dynamite = 7 }

    public static class Items
    {
        public static string Name(ItemType t)
        {
            switch (t)
            {
                case ItemType.MainKey: return "main key";
                case ItemType.Hammer: return "hammer";
                case ItemType.Torch: return "torch";
                case ItemType.CodeNote: return "note";
                case ItemType.SafeKey: return "small key";
                case ItemType.Spring: return "spring";
                case ItemType.Dynamite: return "dynamite";
            }
            return "";
        }
    }

    /// <summary>Anything the player can look at and tap the hand button on.</summary>
    public abstract class Interactable : MonoBehaviour
    {
        public string prompt = "Use";
        public virtual bool Available { get { return true; } }
        public virtual string Prompt() { return prompt; }
        public abstract void Interact();

        protected static Inventory Inv { get { return Inventory.I; } }
        protected static void Msg(string s, float t = 3.5f) { if (NCGame.I != null) NCGame.I.Message(s, t); }
        protected static bool Holding(ItemType t) { return Inventory.I != null && Inventory.I.Held == t; }
    }
}

# Persistent Variables

This plugin provides the ability to store and retrieve script variables that persist across tracks and albums.  This allows things like finding and storing the earliest recording date of all of the tracks on an album.

There are two types of persistent variables maintained - album variables and session variables. Album variables persist across all tracks on an album.  Each album's information is stored separately, and is reset when the album is refreshed. The information is cleared when an album is removed.  Session variables persist across all albums and tracks, and are cleared when Picard is shut down or restarted.

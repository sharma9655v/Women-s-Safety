# Keep kotlinx.serialization generated serializers.
-keepclassmembers class **$$serializer { *; }
-keep,includedescriptorclasses class com.mapforwomen.app.**$$serializer { *; }
-keepclassmembers enum com.mapforwomen.app.** { *; }

# Retrofit / OkHttp.
-keepattributes Signature, InnerClasses, EnclosingMethod, *Annotation*
-dontwarn okhttp3.**
-dontwarn retrofit2.**
-dontwarn org.conscrypt.**
-dontwarn org.bouncycastle.**
-dontwarn org.openjsse.**

# OSMDroid keeps its own rules; keep geo classes usable from XML-free code.
-dontwarn org.osmdroid.**
-keep class org.osmdroid.** { *; }
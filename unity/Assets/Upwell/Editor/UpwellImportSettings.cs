using System;
using UnityEditor;
using UnityEngine;

namespace Upwell.Editor {
    sealed class UpwellImportSettings : AssetPostprocessor {
        void OnPreprocessModel() {
            if(assetPath.StartsWith("Assets/Upwell/Resources/Harbor/",StringComparison.Ordinal)){
                var harbor=(ModelImporter)assetImporter;
                harbor.importAnimation=false;harbor.importCameras=false;harbor.importLights=false;harbor.importBlendShapes=false;
                harbor.meshCompression=ModelImporterMeshCompression.Medium;
                harbor.materialImportMode=ModelImporterMaterialImportMode.ImportStandard;
                harbor.materialLocation=ModelImporterMaterialLocation.InPrefab;
                return;
            }
            if(assetPath=="Assets/Upwell/Resources/Fracture/FractureCartridge.fbx"){
                // Retain the orbital kit's FBX axis convention. The guard and moving controls
                // use the actual machined triangles for their in-world hit surfaces.
                var cartridge=(ModelImporter)assetImporter;cartridge.isReadable=true;
                cartridge.importAnimation=false;cartridge.importCameras=false;cartridge.importLights=false;return;
            }
            if(!assetPath.StartsWith("Assets/Upwell/SourceModels/")&&!assetPath.StartsWith("Assets/Upwell/Terminals/")&&!assetPath.StartsWith("Assets/Upwell/Guideway/"))return;
            var m=(ModelImporter)assetImporter;m.importAnimation=false;m.importCameras=false;m.importLights=false;
            m.bakeAxisConversion=true;m.useFileScale=true;m.globalScale=1;m.isReadable=true;
            m.materialImportMode=ModelImporterMaterialImportMode.ImportStandard;
            m.materialLocation=ModelImporterMaterialLocation.InPrefab;
            m.importNormals=ModelImporterNormals.Import;m.importTangents=ModelImporterTangents.CalculateMikk;
        }
        void OnPreprocessTexture() {
            if(!assetPath.StartsWith("Assets/Upwell/"))return;
            var t=(TextureImporter)assetImporter;string p=assetPath.ToLowerInvariant();
            if(p.Contains("/finish/")) {
                bool depth=p.EndsWith("-depth.png",StringComparison.Ordinal);
                t.textureType=TextureImporterType.Default;t.sRGBTexture=false;t.mipmapEnabled=!depth;t.isReadable=false;
                t.maxTextureSize=4096;t.npotScale=TextureImporterNPOTScale.None;t.textureCompression=TextureImporterCompression.Uncompressed;
                t.filterMode=depth?FilterMode.Point:FilterMode.Bilinear;t.wrapMode=TextureWrapMode.Clamp;return;
            }
            t.maxTextureSize=p.Contains("/environment/")?4096:2048;t.anisoLevel=6;t.mipmapEnabled=true;
            if(p.Contains("/resources/fracture/")){
                // The 768-pixel scans and 2048 × 1536 print sheet already meet GPU block alignment.
                // Keeping their measured dimensions avoids inventing texels and enlarging the hosted archive.
                t.npotScale=TextureImporterNPOTScale.None;t.filterMode=FilterMode.Trilinear;t.anisoLevel=8;
                if(p.EndsWith("/markings.png"))t.wrapMode=TextureWrapMode.Clamp;
                if(p.EndsWith("/dial_lume.png")){t.sRGBTexture=false;t.wrapMode=TextureWrapMode.Clamp;}
            }
            if(p.Contains("normal")||p.EndsWith("/harbor-grain.jpg",StringComparison.Ordinal)){t.textureType=TextureImporterType.NormalMap;t.sRGBTexture=false;}
            else if(p.Contains("roughness")){t.textureType=TextureImporterType.Default;t.sRGBTexture=false;}
            if(p.EndsWith("/earthweatherclimatology.jpg"))t.sRGBTexture=false;
            if(p.EndsWith("/atlanticweather.png")){t.sRGBTexture=false;t.textureCompression=TextureImporterCompression.Uncompressed;t.wrapMode=TextureWrapMode.Clamp;t.npotScale=TextureImporterNPOTScale.None;}
            if(p.Contains("/environment/")){t.wrapModeU=TextureWrapMode.Repeat;t.wrapModeV=TextureWrapMode.Clamp;}
        }
    }
}

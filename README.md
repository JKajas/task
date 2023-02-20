# Recruitment task - thumbnails resize
Project allows uploading images and resizes them to thumbnails. 
## Technologies
Main technologies used in project: 
- Coverage
- Django
- Django REST Framework
- Pillow
- PostgreSQL
## Description
### Models
In the project occurs following models: 
- `Tier` - allows controling presence of image URL in user's list view<br>
- `Size` - allows adding height for specified tiers, which influence creation of thumbnails<br>
- `User` - simple user model, inherited from AbstractBaseUser<br>
- `Image` - core model of API. It has many methods to create thumbnails, to update them if model Tier will be changed, or to generate ImageLink model<br>
- `Thumbnail` - model storages resized images of base Image model.<br>
- `ImageLink` - model storages infomation about validity<br>
Every model of Image and derivatives of image has token through which they are filtered.
### Serializers
There are following serializers:
- `Retrive serializers` - It's a group of serializers that are able to display url but only in case if user is permmited to display attribute declared in their tier. <br>
- `Create and update serializer` - It's serializer responsible for creating models with thumbnails for images.<br>
- `List serializer` - It has nested retrive serializers with similar behaviour.
### Views
Views are doing mentioned things on following endpoints:
- `/admin` <br>
&nbsp;&nbsp;- Allows generating links <br>
&nbsp;&nbsp;- Allows changing presence of image link <br>
&nbsp;&nbsp;- Allows adding sizes to tiers <br>
&nbsp;&nbsp;- Has preview of generated links <br>
- `/users/image/` <br>
GET - Returns URLs for all user's uploaded images<br>
POST - Upload file and return URL in accordance with user's tier(by default uploading is by form data)<br>
**Middleware on POST method** - on POST method is added middleware which allows to upload file by JSON(application/json) in base64 format. Middleware decodes files to native python files. <br>
- `/users/image/<str:token>` <br>
GET - Get image object by token(binary image)<br>
PUT, PATCH - Allows to update Image object<br>
DELETE - Destroing Image object <br>
- `/users/image/<str:token>/generate/` <br>
GET - returns URL to generated LinkImage object which expires within time declared by user <br>
- `/users/thumbnail/<str:token>`<br>
GET - Get thumbnail object by token(binary image)<br>
DELETE - Destroy Thumbnail object<br>
- `/users/binary/<str:token>`<br>
GET - returns binary image<br>
**All retrive methods has decorator checking changes in Tier objects** 
## Installation
1. To run API we just need to write command below:   
 ~~~
 docker compose up
 ~~~
By default we can connect to our API on https://localhost:8000. <br>
The following objects are created on first boot in database:
- Tier: basic, premium, enterprise
- Size: height- 200, 400
2.  To run tests we just need to write command below:
~~~
make test
~~~

#### **Superuser test credentials**
Also during first boot is created superuser with following credentials: <br> 
 **Username:** test <br>
 **Password:** Test123<br>


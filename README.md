---
# Mealdeals #
---

![logo](static/media/img/logo.jpg)

---
## Contents ##
---

* [UX](#User-Experience)
    * [Project Goals](#project-goals)
    * [User Goals](#user-goals)
    * [User Stories](#user-stories)
    * [User Requirements and Expectations](#requirements)
    * [Design Choices](#design-choices)
        * [Fonts](#fonts)
        * [Icons](#icons)
        * [Colors](#colors)
* [Structure](#structure)
    * [Page Structure](#page_structure)
    * [Database and schema](*db_schema)
    * [Wireframing](#wireframing)
* [Features](#features)
    * [Features that have been developed](#developed)
    * [Features that will be implemented in the future](#implemented)
* [Technologies](#technologies)
* [Testing](#testing)
* [Issues](#issues)
* [Deployment](#deployment)
* [Credit](#credits)

---
---
<a name="User-Experience"></a>
## UX (User Experience) ##
---
---

<a name="project-goals"></a>
### Project Goals ###
---

This website is designed so that restaurants can have a space to advertise thier deals, and bring foot traffic through thier doors 

The **goal** for this project is to allow restaurants the ability to advertise their restaurant and thier ideas on a platform which is not social media. <br>
The website also gives the restaurants the access to change thier deals without any hassle, but most important it is a place where the restaurants are charged
a flat rate for monthly subscribions instead of being "charged per voucher" bought and have a portion of their hard earned profit put towards bringing in people.

---
<a name="user-goals"></a>
### User Goals ###
---

For the UX on this project I wanted to create a simple and user friendly site. My target audience is young and mature adults. <br>
The site also allows for restaurant customers to find good and decent deals in thier area!!

#### Scope ####
* An Eye catching landing page
* Mass-displaying all or filtered deals. Lines of relatively small images, with option to click and view or like
* Search, filter and sort deals.
* Detailed profile for restauranteurs on top of the simple registration.
* Dedicated page for uploading new deals
* Checkout with card payment.
* Full page Deal view including the Name of the restaurant, address and contact details as well as the Deal description, price and valid till, options.
* Legal framework is also included, with links to privacy policies and FAQs, as well as corporate info in the about us section of the website.

#### Clients ####
* **View specific deals** with **quick searches** within the **Category and Area** they are looking for, instead of searching through all the deals.
* **Being excited** to find new deals and **share** these deals with their friends.
* **Veiw** the full list of deals on the home page
* **Find company info** from the deal such as name of restaurant, address, telephone number, website
* **View individual deal Info** from the deal such as T&C's, price, and end time for the promotion 
* **Contact us** for expert marketing advise and we will design any deals for you at a small fee.
<br>

#### Restaurant Management Profiles ####
* Easily **Register & Create** a Profile, having a restaurant specific profile.
* Easily **Login or Logout** access to account infomation
* Easily **recover my password** in case I forget it.
* Recieve **an Email confirmation** to verify that my account registeration was successful.
* **Easily** pay for the subscribtion costs on signing up
* **Receive** and email confirmation of purchase to keep for records and accounting.
* **Add, Edit and Delete** Company infomation as needed in a **personalized User profile**
* **Add, Edit and Delete** Deals periodicaly

#### Out of Scope topics ####
* order processing after checkout and the bag was excluded, as one of the steps in the payment journey.
* Potential further features:

    * Coupon code for promotions,
    * Discount for multi-buys.
* Marketing the site itself and utilising advertising opportunities within the site is out of scope, therefore the links to social media sites are home based links.

---
<a name="user-stories"></a>
### User Stories ### 
---

* The **Clients user** wants an **attractive website** with a **non-distracting** background.
* The **Clients user** wants to see **clear instructions** on how to drill down into further infomation on deals within the website.
* The **Clients user** wants there to be a **search box** so that the user can quickly identify **deals**.
* The **Clients user** wants to be able to **sort by** categories or restaurant name.
* The **Clients user** wants to start **finding deals immedaitely**. 
* The **Clients user** wants to see the **latest deals** added.
* The **Clients user** wants a **conveint sized deal box** to be able to read the Deal clearfully.
* The **Clients user** wants to know the **Deals** details such as **T&C's, price, and end time** for the promotion.
* The **Clients user** wants to get a maximum of advantage of the **Mealdeals cloud**.
<br>
* The **Admin user** wants to know the **time period** of the deal before **deciding** on continuing with the specific deal.
* The **Admin user** wants to **have the possibility** of thier **own profile** where their deals come up first.
* The **Admin user** wants to **know** if **their Deals has been submitted**.
* The **Admin user** wants to know the **deals** details such as **name of restaurant, address, telephone number, website**
* The **Admin user** wants to **easily add, edit and delete their own Deals** on the website.
* The **Admin user** wants to **have the possibility** to **upload pictures**.

---
<a name="requirements"></a>
### Research ###
---

* When developing this **website**, I kept in mind that the aesthetic should be inspired by similar Deal and coupon hubs on the internet. 
* I tried to create a **simple and easy feel** to for a cleaner approach for the landing page.
* I checked **previously made coupon websites** such as [**groupon.ie**](https://www.groupon.ie//) and used **my own experience** as a trained chef and restauranteur.

![Research](media/readme/Groupon.png)
![Research](media/readme/first_table.png)
![Research](media/readme/dealy.png)

---
<a name="design-choices"></a>
### Design Choices ###
---

<a name="fonts"></a>
### Fonts ###

* The **landing page** is using the classic website **Google Fonts** **#** for the H1 and H3. 
* I paired it with the **Google Fonts** **Crimson & Oswald** for readability.
* I kept the **Oswald** font for **better user experience**

<a name="icons"></a>
### Icons and Images ###

* The **Favicon** used on the website are provided by [**Canva**](https://canva.com/) and called by using url_for.
* The **image** used for the **landing page** is a created **image** from the image bank [**Canva**](https://canva.com/). 

<a name="colors"></a>
### Colors ###

* The **color scheme** used for the website is a sleek **deal website palette** composed of a combination of **Red and whites** 
* For the **title** and the **logo** I used a **dark burgandy red** on the **a white background**.
* I specifically chose these colors as Red is a colour at stimulates appetite in humans, but I wanted it a dark red as I still wanted to convey a relaxed atmosphere.

---
---
<a name="structure"></a>
## Structure ##
---
---

<a name="page_structure"></a>
### Page Structure ###
---

#### Filtering and browsing ####
There are two types of users and I wanted to give clear path to start using the site with Call To Action for both groups. Potential deal shoppers are directed to the Search & browsing, while potential restuaranteurs are shown an eye-catchy banner with a popping CTA button.

#### Home page ####
Many similar sites (competitors) are trying to showcase wide range of services and options, therefore loosing focus and probably loosing potential subscriptions and users by not inviting them to further explore the site. My clear goal here is to lead users to check out more deals.

#### Detailed view ####
Clicking on any of the deals on the home page brings the user to the deal details page, displaying all the available information about each deal. 

#### Potential contributors ####
Potential contributors have a flow of action to fully utilize the page and achieve their goals. They have a strictly limited access to the part of the database that concerns their artwork and therefore can perform CRUD operations.

* Create new entry: upload image and provide details
* Read (Display) entries - the detailed view with personal information
* Update entries - making changes to their existing records
* Delete entries – delete items from the database 


---
<a name="db_schema"></a>
### Database and schema ###
---

![Inspiration](media/readme/eat_drink_deals.png)

---
<a name="wireframing"></a>
### Wireframing ###
---
For **wireframing** I used the tool [**Balsamiq**](https://balsamiq.com/).

Please follow the link to find the preview [here] 

href = https://balsamiq.cloud/srsmfvs/pt96bgn/r7C4D

* Herewith the **wireframe** and I pushed a few changes for better readability and engagement:
* I added **a jumbotron hero image** on the landing page.
* I added **a full-screen background image** on all the other pages.
* I used a **form** to allow for the user to add & edit Deals.
* I added an easy link to **upload** videos.

### Landing Page ###
!["Wireframe LandingPage"](media/readme/MealdealsWireframe.png)
### Search results ###
!["Wireframe SearchLandingPage"](media/readme/MealdealsWireframe1.png)
### Deal Page ###
!["Wireframe Deal"](media/readme/MealdealsWireframe2.png)
### Registeration Page ###
!["Wireframe Registeration"](media/readme/MealdealsWireframe3.png)
### Registeration Payment Page ###
!["Wireframe Payment Page"](media/readme/MealdealsWireframe4.png)
### Add deal profile Page ###
!["Wireframe profile"](media/readme/MealdealsWireframe5.png)
### Contact us Page ###
!["Wireframe profile"](media/readme/MealdealsWireframe6.png)


<a name="features"></a>
## Features ## 
---

<a name="developed"></a>
### Implemented Features ###

* **Responsiveness** on all screen sizes.
* **large title** for attractiveness and engagement.
* **Suggested recipes** on landing page as an introduction.
* **User login/logout** so that users can keep a tally of their own recipes added and videos uploaded.
* **Input Recipes** to the website.
* **Edit Recipes** to the website.
* **Search Recipes** on the Website.
* **Instructions** so that the user can grasp the concept immedaitely.
* **Immedaite** recipes with Easy and simple instructions to make the recipe.
* **Download success** notation when recipe has successfully saved to the database
* **upload picture** with the recipe to give people a sense of what can be acheived with their recipe.
* **upload video** allows users to upload videos of themselves creating a recipe.

<a name="implemented"></a>
### Future implemented features ###

* **Feature 1** - **Rating system** for others to be able to rate the recipe success.
* **Feature 2** - **Comment box** and **messages notifications** below the recipes for users to interact with each other.
* **Feature 3** - **Favorites** for user to quickly reference recipes they enjoyed or still want to Experiment with.
* **Feature 4** - **Input Videos** to the website.

<a name="technologies"></a>
## Technologies used ##

* [HTML](https://developer.mozilla.org/en-US/docs/Web/HTML)
* [CSS](https://developer.mozilla.org/en-US/docs/Web/CSS)
* [Javascript](www.javascript.com)
* [JQuery](https://jquery.com/)
* [Python](https://www.python.org/)

**Tools & Libraries**

* [Bootstrap](https://getbootstrap.com/)
* [Font-Awesome](https://fontawesome.com/icons?d=gallery)
* [Google fonts](https://fonts.google.com/)
* [Git](https://git-scm.com/)
* [PNGtree](https://PNGtree.com/)
* [Flask](https://pypi.org/project/Flask/)
* [Canva](https://canva.com)
* [MongoDB](https://cloud.mongodb.com/)

<a name="testing"></a>

## Testing ##
---

*I used **pep8online.com** to test my Python code validator with no issues - http://pep8online.com/checkresult
![pep8](static/img/pep8_test.png)
* I tested the python code with **Python Debugger** - https://realpython.com/python-debugging-pdb/
![pdb](static/img/pdb_debugger.png)
* Also used this **Automated Testing** to test my flask applications - https://www.patricksoftwareblog.com/unit-testing-a-flask-application
![test_flask](static/img/test_flask.png)
* I used **Pylint** to lint my code by Linting my python code - http://pylint.pycqa.org/en/latest/
![test_Pylint](static/img/pylint.png)
* I tested the responsiveness of the website by using the [**Google Chrome Developer Tool**](https://developers.google.com/web/tools/chrome-devtools) as well as the plug-in **Unicorn Revealer** to control my overflow and the website [**Am I Responsive**](http://ami.responsivedesign.is/). 
![AmIresponsive](static/img/amIresponsive.png)
* I also tested my website on **different browsers and real devices** : **Iphone 6s, Ipad Pro 12", Ipad Mini, Google Chrome, Safari, Mozilla Firefox and Samsung A70.**
* I used a first **dirty version** of this project on **Gitpod** and **refactored** my code **step by step** to remove any **useless classes**
* I tested my CSS file and my HTML files using [**CSS Validator**](https://jigsaw.w3.org/css-validator/) and [**HTML Validator**](https://validator.w3.org/) then fixed the issues needed to be fixed.
![test_Html](static/img/errors_val_w3.png)
![test_CSS](static/img/errors_val_w3_css.png)
* I tested every **functions** of my script.js using multiple **console.log** and checking for **errors** in the **Google Chrome console**.
* I passed my deployed app through **Lighthouse** with the follwoing results
![lighthouse](static/img/lighthouse.png)
* All pages passed the HTML,CSS and Python validator final test with no major issues.

**Responsiveness**

* **Implementation** 

    * I used **Bootstrap** as well as **flexbox and custom CSS media queries** to ensure that the website didn't break on all screen sizes.

![landingPage](static/img/home_page_response.png)
![landingPage](static/img/home_page_response2.png)

**Landing Page**

![landingPage](static/img/home_page.png)
![landingPage](static/img/home_page_footer.png)

* **Implementation** 

    * I wanted to keep it clean and neat with the landing page displaying the newest and latest recipes.<br>
    * The UI has been created in HTML5 and CSS3 and by using bootstrap all tiles are responsive on all screen sizes.<br>
    * As stated above, I wanted to recreate a neighbourhood profile where friends, neighbours and relatives can swap and share their favourite recipes, simply and easily<br>
    * User does not have to register if they just want to veiw recipes all recipes are free.<br>
    * Landing page was responsive and working as expected<br>

**Add register**

![Recipes](static/img/register.png) 

* **Implementation**

    * To start adding your own recipes you would need to register.<br>
    * Once registered you would have to log in<br>
    * User is informed if registeration is successful if flash message appears "user successfully added" else flashes "user name already used"<br>
    * Register and Log-in page was responsive and working as expected<br>

**Profile for normal users**

![Profile](static/img/profile.png) 
![Profile](static/img/profile_display.png) 

* **Implementation**

    * This is where the real fun begins, as a user you can <br>
        1. Thier **own profile** where their recipes come up first. <br>
        2. **Easily Add and Edit their own recipes** to the website. <br>
        3. **Have the possibility** to **upload pictures** <br>
        4. **Easily Delete their own recipes** if they no longer want to be on the website. <br>
    * Profile page was responsive and working as expected<br>

**Profile for Admin**

![Profile](static/img/profile_admin.png) 

* **Implementation**

    * This is where the Admin can see the listings page<br>
        1. Admin also has thier **own profile** where their recipes come up first. <br>
        2. From Listings Admin can **Easily Add and Edit all recipes** on the website. <br>
        3. **Have the possibility** to edit **upload pictures** which do not subscribe to the user agreement on the page <br>
        4. **Easily Delete any recipes** if the recipe does not prescribe to the user agreement and is no longer allowed on the website. <br>
    * Admin page was responsive and working as expected<br>

**Add recipes & Edit Recipes**

![Add Recipes](static/img/add_recipes.png) 
![Edit Recipes](static/img/edit_recipes.png) 

* **Implementation**

    * Both the add_recipe and the edit_recipe, have the same framework and based on the same template. <br>
    * edit_recipe does however pulls all the values from the DB so that User is aware what recipe they are editing <br>

    * This is the second step of the **CRUD** functionality, users can Add or edit the following: <br>
        1. Recipe name <br>
        2. Category <br>
        3. Prep time <br>
        4. Cooking Time <br>
        5. Difficulty <br>
        6. Serves <br>
        7. Ingredients <br>
        8. Add ingredient fields (add more then one or extra fields) <br>
        9. Instructions <br>
        10. Add Instructions fields (add more then one or extra fields)<br>

    * Also I have added a button for the user tochange mind and go back to profile. <br>
    * add_recipe and the edit_recipe pages was responsive and working as expected<br>

<a name="issues"></a>
## Issues ##
---

**During development**

* I had a major issue with my MongoDB file whilst setting up the database because of this issue: <br>

**Issues**

I did not understand what was going on as my form was good and allowing me to add into the fields,<br> however when I submitted it was not sending it to the
database and saving it in the collections?

![RecipeForm](static/img/upload_recipe.png)

* To understand the error I went thorugh the code again and fixed it by creating "action" in the form to allow the method to "POST", later refactoring "input" to "add_recipes" for simplified reading<br>
* Then I refactored the code for one value such as ingredient & instruction, this name creates an array. This solved the issue for multiple variables to be added into the Database and when called listing all items in the array, and not seperating the values out as individual strings. <br>
* I also refactored the uppercase to lowercase, plurals and used_ to_seperate the variables wording rather. I refactored the numerical data into Intergers by using the int() option in python. <br>
* I also added timestamps and created_by to reference when the user is logged on, timestamps to allow the users to see the latest recipe added and created_by for users to veiw all their own recipes in their profile. <br>

![RecipeForm](static/img/upload_fix.png)
![RecipeForm](static/img/solve_input.png)

I was having an issue with the search elements once I had refactored the code for add_recipe and edit_recipe. Pagination being a big error, as I had added pagination to the index page.

![Indexes](static/img/search_issues.png)

* After many attempts I decided to rather add a seperate html dedicated to search results instead trying to forced the system to display the index page. <br>
* Once fixed the search was not bearing any results, very confused as no errors were appearing. Thus I assumed the issue must lie with the query. <br>
* And yes, I had forgotten to refactor the orginal indexes in MongoDB, how the user is able to search mulitple questions, name, category, ingredient and even any instruction. <br>

![Search](static/img/search_fixes.png)
![DB](static/img/index_refactor.png)

I also has few errors passing through my GitPod, basic house cleaning fixed most of the issues very quickly

![Html](static/img/indexErrors.png)
![PY](static/img/runpyErrors.png)

After my mentor call and my peer-code-review I realized that I needed to add some comments via Docstring for understanding of my code. <br>
and used this website to assist me Docstring conventions - https://www.python.org/dev/peps/pep-0257/ <br>

![Docstring](static/img/docstring.png)

## Deployment ##
---
**RecipeCloud** was developed on **GitPod**, using **GitHub** to host the repository and deployed on **GitHub Pages**.
**Heroku** made the deployment extremely painless:

* Connect to [**Heroku**](https://dashboard.heroku.com/apps)
* Click new/ **create new APP**
* Add the new app name and choose a region, In my case **Europe**
* While the app is being generated you will need to **Config Vars** by going to **settings**
* Config vars change the way your app behaves. In addition to creating your own, some add-ons come with their own
* In **Config vars** you need to add the **ID,PORT,MONGODB_NAME,MONGO_URI,SECRET_KEY**
* Now to **Deploy** find deployment method choose **GitHub** sign into your GitHub.
* Selected the repository **JustWhittaker/PRO3-RecipeCloud**
* In the **GitHub Pages** I selected **Master Branch** and **/root** in the dropdown menu and clicked **Save**
* Click on **"Automatic Deploys"** below 
* I waited 2 minutes.
* **The website is now live on https://recipe-cloud-pro.herokuapp.com/**.

**Cloning** No issues:

* Why do we is it important to be able to clone successfully first **Collaboration** with team members if you are working in a scrum and secondly **Assist** other developers to use my main project to grow their own version.
* In my repository **JustWhittaker/PRO3-RecipeCloud**, click on the **"Code** green button, **copy in clipboard the HTTPS link**, open your **IDE** and look through my files.
* The link : **https://github.com/JustWhittaker/PRO3-RecipeCloud.git**

<a name="credits"></a>
## Credits ##
---

**Text Credits:**

* All text content has been written by Justin Whittaker.

I received inspiration and technical knowledge for this project from the following platforms
1. Bootstrap <br>
https://mdbootstrap.com/docs/standard/forms/input-fields/<br>
https://getbootstrap.com/docs/4.3/components/card/<br>
https://getbootstrap.com/docs/4.3/components/dropdowns/<br>
https://www.w3schools.com/bootstrap/bootstrap_ref_css_images.asp <br>
https://www.w3schools.com/bootstrap4/bootstrap_navbar.asp <br>
https://stackoverflow.com/questions/10099422/flushing-footer-to-bottom-of-the-page-twitter-bootstrap#:~:text=The%20simplest%20technique%20is%20probably,the%20footer%20to%20the%20bottom.

2. Django Basics <br>
https://docs.djangoproject.com/en/3.1/intro/tutorial01/<br>
https://www.ordinarycoders.com/blog/article/build-a-django-contact-form-with-email-backend<br>
https://stackoverflow.com/questions/21938028/how-can-i-get-a-favicon-to-show-up-in-my-django-app<br>
https://www.geeksforgeeks.org/python-uploading-images-in-django/<br>
https://stackoverflow.com/questions/36665889/collectstatic-error-while-deploying-django-app-to-heroku

3. Python research <br>
    1. CodeInstitute Django Fundamentals <br>
    2. https://randomkeygen.com/ <br>
    3. Docstring conventions - https://www.python.org/dev/peps/pep-0257/ <br>

4. Better Git Commit terms <br>
http://karma-runner.github.io/5.0/dev/git-commit-msg.html

5. Dependencies <br>
    1. Django <br>
    2. JQuery (html js middleware) <br>
    3. bootstrap <br>

6. Other platforms <br>
https://policymaker.io/privacy-policy-ready/ <br>
https://favicon.io/favicon-generator/ <br>
https://devcenter.heroku.com/articles/heroku-postgresql#connecting-in-python<br>

**Many thanks to:**

* My mentor **Ignatius Ukwuoma** for his patience and kindness
* **AudreyLL88** for her very inspiring ReadME
* **Code Institute Slack community** for the technical and emotional support
* **Code Institute Tutors** Cormac, Tim, Sam, Johann and Milkos were fantastic help
* **Alishia Whittaker**, for the Graphic design and stock images from Canva and your support through all my studies

**Site for educational purposes only!**
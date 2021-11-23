The text below is mostly taken from the official [NATS docs](https://docs.nats.io/) 
[NATS](http://nats.io) is a high-performance messaging system written in Golang. NATS is very easy to use, has very high bandwidth, and easily scales. It has 48 well-known clients, 11 of which are supported by the maintainers. NATS offers delivery guarantees, high availability, and fault tolerance. NATS is used on the web, IoT, and blockchain.
### **Subject**

Subject in NATS is like a topic for Kafka or URL for HTTP. At its simplest, a subject is just a string of characters that form a name that publishers and subscribers can use to find each other.

### Subject Hierarchies

For example, a world clock application might define the following to logically group related subjects:

```jsx
time.us
time.us.east
time.us.east.atlanta
time.eu.east
time.eu.warsaw
```

### Wildcards

NATS provides two wildcards that can take the place of one or more elements in a dot-separated subject. Subscribers can use these wildcards to listen to multiple subjects with a single subscription but publishers will use a fully specified subject, without the wildcard.

### Matching a single token

The first wildcard is <span class="red">`*`</span> which will match a single token. For example, if an application wanted to listen for eastern time zones, they could subscribe to <span class="red">`time.*.east`</span>, which would match <span class="red">`time.us.east`</span> and <span class="red">`time.eu.east`</span>.

![https://gblobscdn.gitbook.com/assets%2F-LqMYcZML1bsXrN3Ezg0%2F-LqMZac7AGFpQY7ewbGi%2F-LqMZftc5Yt_LEI224RE%2Fsubjects2.svg?alt=media](https://gblobscdn.gitbook.com/assets%2F-LqMYcZML1bsXrN3Ezg0%2F-LqMZac7AGFpQY7ewbGi%2F-LqMZftc5Yt_LEI224RE%2Fsubjects2.svg?alt=media)

### Matching multiple tokens

The second wildcard is <span class="red">`>`</span> which will match one or more tokens, and can only appear at the end of the subject. For example, <span class="red">`time.us.>`</span> will match <span class="red">`time.us.east`</span> and <span class="red">`time.us.east.atlanta`</span>, while <span class="red">`time.us.*`</span> would only match <span class="red">`time.us.east`</span> since it can't match more than one token.

![https://gblobscdn.gitbook.com/assets%2F-LqMYcZML1bsXrN3Ezg0%2F-LqMZac7AGFpQY7ewbGi%2F-LqMZfteO4zWGmIbkFHf%2Fsubjects3.svg?alt=media](https://gblobscdn.gitbook.com/assets%2F-LqMYcZML1bsXrN3Ezg0%2F-LqMZac7AGFpQY7ewbGi%2F-LqMZfteO4zWGmIbkFHf%2Fsubjects3.svg?alt=media)

### Monitoring and wire taps

Subject to your security configuration, wildcards can be used for monitoring by creating something sometimes called a wire tap. In the simplest case, you can create a subscriber for <span class="red">`>`</span>. This application will receive all messages - again, subject to security settings - sent on your NATS cluster.

### Mix wildcards

The wildcard <span class="red">`*`</span> can appear multiple times in the same subject. Both types can be used as well. For example, <span class="red">`*.*.east.>`</span>will receive <span class="red">`time.us.east.atlanta`<span class="red"></span>.